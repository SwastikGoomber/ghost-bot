"""
StateManager — the authoritative store for all user and cone state.

Responsibilities:
- Get-or-create UserState for any (platform, user_id, username) triple.
- Persist state to MongoDB (or a local JSON fallback if no URI is set).
- Trigger and apply summary updates via the Gemini summary client.
- Manage cross-platform account linking.
- Expose cone_data so ConeManager can read/write it.

MongoDB document layout (ghost_bot.user_states, _id="current_states"):
{
  "discord_<id>": { UserState.model_dump() },
  "twitch_<id>":  { UserState.model_dump() },   # if not linked to a Discord account
  "cone_data":     { "<discord_id>": ConeData.model_dump() },
  "pending_links": { "<twitch_username>": "<discord_id>" }
}

Notes:
- Linked accounts share the same Python UserState object in memory.
  On save, both keys write the same Pydantic model (idempotent).
- On load, Twitch keys that reference a Discord account are re-linked.
- `cone_data` and `pending_links` are separate top-level keys in the document.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..utils.exceptions import StateError, DatabaseError
from ..utils.models import (
    ConeData,
    Message,
    Platform,
    PlatformIdentity,
    UserState,
    UserSummaries,
)
from . import db as _db_module

logger = logging.getLogger(__name__)

_FALLBACK_FILE = "user_states.json"

# Common English words that will never be a username/alias.
# Kept intentionally short — only words likely to appear as >= 4-char tokens
# that could accidentally fuzzy-match a short username.
_TEXT_SCAN_STOP_WORDS: frozenset[str] = frozenset({
    "have", "just", "like", "that", "this", "with", "from", "they",
    "them", "been", "will", "your", "what", "when", "where", "know",
    "think", "about", "really", "would", "could", "should", "their",
    "some", "then", "than", "more", "said", "come", "into", "time",
    "does", "good", "here", "over", "back", "also", "well", "even",
    "only", "through", "before", "after", "never", "always", "very",
    "just", "were", "with", "which", "there", "while", "those", "these",
    "both", "make", "made", "much", "most", "such", "each", "same",
    "ghost",  # Ghost itself — never a cone/mention target in text scan
})


class StateManager:
    def __init__(self) -> None:
        # platform_key (e.g. "discord_123456") → UserState
        # Linked accounts share the *same* UserState object.
        self._users: dict[str, UserState] = {}

        # discord_id (numeric string) → ConeData
        self.cone_data: dict[str, ConeData] = {}

        # twitch_username.lower() → discord_id
        self._pending_links: dict[str, str] = {}

        self._use_mongo = bool(os.environ.get("MONGODB_URI"))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def load_states(self) -> None:
        """Load all state from persistent storage."""
        self._users = {}
        self.cone_data = {}
        self._pending_links = {}

        try:
            if self._use_mongo:
                data = await self._mongo_load()
            else:
                data = self._file_load()
        except (DatabaseError, FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("Failed to load states: %s — starting fresh.", exc)
            return

        self._pending_links = data.get("pending_links", {})

        # Deserialise cone_data
        for key, cone_dict in data.get("cone_data", {}).items():
            try:
                self.cone_data[key] = ConeData.model_validate(cone_dict)
            except Exception as exc:
                logger.warning("Could not deserialise cone entry '%s': %s", key, exc)

        # First pass — load all Discord states
        discord_states: dict[str, UserState] = {}
        for key, user_dict in data.items():
            if key in ("pending_links", "cone_data"):
                continue
            if key.startswith("discord_"):
                state = _deserialise_user_state(user_dict)
                if state:
                    self._users[key] = state
                    discord_id = state.identifiers.get("discord", PlatformIdentity(
                        user_id="", username="", display_name=""
                    )).user_id
                    if discord_id:
                        discord_states[discord_id] = state

        # Second pass — load Twitch states, linking to Discord where possible
        for key, user_dict in data.items():
            if key in ("pending_links", "cone_data") or key.startswith("discord_"):
                continue
            if key.startswith("twitch_"):
                # Check if this Twitch account is linked to a Discord account
                identifiers = user_dict.get("identifiers", {})
                discord_id = identifiers.get("discord", {}).get("user_id")
                if discord_id and discord_id in discord_states:
                    # Re-link: point this twitch key to the existing Discord state object
                    self._users[key] = discord_states[discord_id]
                else:
                    state = _deserialise_user_state(user_dict)
                    if state:
                        self._users[key] = state

        unique = len({id(s) for s in self._users.values()})
        logger.info(
            "Loaded %d unique users (%d keys), %d cone entries, %d pending links.",
            unique, len(self._users), len(self.cone_data), len(self._pending_links),
        )

    async def save_states(self) -> None:
        """Persist all state to storage."""
        data: dict = {}

        # Serialise users — track object identity to avoid duplicate work
        serialised_ids: set[int] = set()
        for key, state in self._users.items():
            if id(state) not in serialised_ids:
                serialised_ids.add(id(state))
            # Always write the key; linked accounts write the same data under two keys
            data[key] = state.model_dump(mode="json")

        if self.cone_data:
            data["cone_data"] = {k: v.model_dump(mode="json") for k, v in self.cone_data.items()}

        if self._pending_links:
            data["pending_links"] = self._pending_links

        try:
            if self._use_mongo:
                await self._mongo_save(data)
            else:
                self._file_save(data)
        except Exception as exc:
            logger.error("Failed to save states: %s", exc)
            raise StateError(f"State persistence failed: {exc}") from exc

    # ------------------------------------------------------------------
    # User state access
    # ------------------------------------------------------------------

    async def get_user_state(
        self,
        user_id: str,
        username: str,
        platform: str,
        nickname: Optional[str] = None,
    ) -> tuple[UserState, Optional[str]]:
        """
        Get or create a UserState for a user. Returns (state, link_notification_or_None).

        Link notifications are returned (not sent) so the platform layer can format them.
        """
        platform_key = f"{platform}_{user_id}"

        if platform_key in self._users:
            state = self._users[platform_key]
            # Ensure shared-object links are consistent
            self._relink_if_needed(state)
            return state, None

        # Try to auto-link by matching username/nickname
        existing = self._find_matching_user(username, nickname)
        if existing:
            existing_platform = next(iter(existing.identifiers))
            existing_name = existing.identifiers[existing_platform].username
            existing.identifiers[platform] = PlatformIdentity(
                user_id=user_id,
                username=username,
                nickname=nickname,
                display_name=nickname or username,
            )
            existing.name_variants = list(set(existing.name_variants + _name_variants(username)))
            self._users[platform_key] = existing
            notification = (
                f"Discord account automatically linked with Twitch account {existing_name}"
                if platform == "discord"
                else f"Twitch account automatically linked with Discord account {existing_name}"
            )
            return existing, notification

        # Create a fresh state
        state = UserState(
            identifiers={
                platform: PlatformIdentity(
                    user_id=user_id,
                    username=username,
                    nickname=nickname,
                    display_name=nickname or username,
                )
            },
            primary_name=username,
            name_variants=_name_variants(username),
        )
        self._users[platform_key] = state
        return state, None

    async def add_message(
        self,
        platform_key: str,
        content: str,
        from_bot: bool,
        username: str,
    ) -> None:
        """Append a message to the user's history and persist."""
        state = self._users.get(platform_key)
        if state is None:
            logger.warning("add_message: no state found for key '%s'", platform_key)
            return
        state.recent_messages.append(
            Message(content=content, from_bot=from_bot, username=username)
        )
        state.last_interaction = datetime.now()
        await self.save_states()

    def needs_summary_update(self, platform_key: str) -> bool:
        """True when the user's message history has reached the configured trigger count."""
        from ..utils.config import get_config
        cfg = get_config()
        state = self._users.get(platform_key)
        if state is None:
            return False
        return len(state.recent_messages) >= cfg.memory.summary_trigger_count

    async def update_summaries(self, platform_key: str) -> tuple[bool, str]:
        """
        Summarise the user's recent messages via Gemini and persist the result.

        Returns (success, human_readable_message).
        """
        from ..utils.config import get_config
        from ..utils.llm import get_llm_client
        from pathlib import Path

        cfg = get_config()
        state = self._users.get(platform_key)
        if state is None:
            return False, "User not found."

        try:
            # Load summarizer prompt template
            prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "summarizer.md"
            template = prompt_path.read_text(encoding="utf-8")

            formatted_messages = "\n".join(
                f"{'Ghost' if m.from_bot else m.username}: {m.content}"
                for m in state.recent_messages
            )

            prompt_text = template.format(
                current_relationship=state.summaries.relationship,
                current_conversation=state.summaries.last_conversation,
                formatted_messages=formatted_messages,
            )

            summary_client = get_llm_client("summary")
            response_text = await summary_client.generate(
                messages=[{"role": "user", "content": prompt_text}]
            )

            relationship, conversation = _parse_summary_response(response_text)

            if not relationship or not conversation:
                logger.warning("Summary response could not be parsed for %s.", platform_key)
                return False, "Failed to parse summary response."

            state.summaries = UserSummaries(
                relationship=relationship,
                last_conversation=conversation,
            )
            # Keep only the most recent N messages after summarisation
            state.recent_messages = state.recent_messages[-cfg.memory.messages_kept_after_summary:]
            await self.save_states()

            logger.info("Summaries updated for %s.", platform_key)
            return True, "Summary updated successfully!"

        except Exception as exc:
            logger.error("update_summaries failed for %s: %s", platform_key, exc)
            return False, f"Error updating summaries: {exc}"

    async def merge_summaries(self, summary1: UserSummaries, summary2: UserSummaries) -> UserSummaries:
        """
        Merge two UserSummaries objects into one using Gemini.

        Used when linking a Discord and Twitch account that both have existing history.
        Falls back to summary1 if the merge call fails.
        """
        from ..utils.llm import get_llm_client

        prompt = (
            "Combine these two summaries of the same user from different platforms "
            "into a single coherent summary.\n\n"
            f"[SUMMARY SET 1]\n"
            f"Relationship: {summary1.relationship}\n"
            f"Last Conversation: {summary1.last_conversation}\n\n"
            f"[SUMMARY SET 2]\n"
            f"Relationship: {summary2.relationship}\n"
            f"Last Conversation: {summary2.last_conversation}\n\n"
            "Provide the combined summary in this exact format:\n"
            "[RELATIONSHIP_SUMMARY]\n(combined relationship summary)\n\n"
            "[CONVERSATION_SUMMARY]\n(combined conversation summary)"
        )
        try:
            client = get_llm_client("summary")
            response = await client.generate(messages=[{"role": "user", "content": prompt}])
            relationship, conversation = _parse_summary_response(response)
            if relationship and conversation:
                return UserSummaries(relationship=relationship, last_conversation=conversation)
        except Exception as exc:
            logger.error("merge_summaries failed: %s", exc)
        return summary1  # safe fallback

    # ------------------------------------------------------------------
    # Account linking
    # ------------------------------------------------------------------

    async def create_link_request(self, discord_id: str, twitch_username: str) -> bool:
        """Register a pending link: Discord user wants to link with Twitch account."""
        self._pending_links[twitch_username.lower()] = discord_id
        await self.save_states()
        logger.info("Link request: discord=%s twitch=%s", discord_id, twitch_username)
        return True

    async def confirm_link_request(self, twitch_id: str, twitch_username: str) -> tuple[bool, str]:
        """
        Confirm a pending link. Called when the Twitch user types !confirm_link.
        Merges any existing Twitch history into the primary Discord state.
        """
        twitch_username = twitch_username.lower()
        discord_id = self._pending_links.get(twitch_username)
        if not discord_id:
            return False, "No pending link request found."

        discord_key = f"discord_{discord_id}"
        twitch_key = f"twitch_{twitch_id}"

        if discord_key not in self._users:
            return False, "Discord user not found."

        primary = self._users[discord_key]

        # Merge any existing Twitch state
        if twitch_key in self._users:
            twitch_state = self._users[twitch_key]
            if id(twitch_state) != id(primary):
                primary.recent_messages.extend(twitch_state.recent_messages)
                primary.recent_messages.sort(key=lambda m: m.timestamp)
                primary.summaries = await self.merge_summaries(primary.summaries, twitch_state.summaries)
                primary.name_variants = list(set(primary.name_variants + twitch_state.name_variants))

        primary.identifiers["twitch"] = PlatformIdentity(
            user_id=twitch_id,
            username=twitch_username,
            display_name=twitch_username,
        )
        self._users[discord_key] = primary
        self._users[twitch_key] = primary  # shared object

        del self._pending_links[twitch_username]
        await self.save_states()
        return True, "Accounts linked! Conversation history and summaries have been merged."

    async def unlink_accounts(self, platform_key: str) -> bool:
        """Separate a linked Discord+Twitch account back into two independent states."""
        state = self._users.get(platform_key)
        if not state:
            return False

        discord_data = state.identifiers.get("discord")
        twitch_data = state.identifiers.get("twitch")

        if not (discord_data and twitch_data):
            return False

        discord_key = f"discord_{discord_data.user_id}"
        twitch_key = f"twitch_{twitch_data.user_id}"

        # Split: new independent Twitch state with shared history
        twitch_state = UserState(
            identifiers={"twitch": twitch_data},
            primary_name=twitch_data.username,
            name_variants=_name_variants(twitch_data.username),
            summaries=state.summaries.model_copy(),
            recent_messages=list(state.recent_messages),
        )

        # Discord state keeps only its own identity
        state.identifiers = {"discord": discord_data}
        self._users[discord_key] = state
        self._users[twitch_key] = twitch_state

        await self.save_states()
        return True

    # ------------------------------------------------------------------
    # Text mention scanning
    # ------------------------------------------------------------------

    def scan_message_for_users(
        self,
        message: str,
        exclude_discord_id: Optional[str] = None,
    ) -> list[str]:
        """
        Scan free-form text for user mentions by name, variant, or alias.

        Two passes:
        1. Exact lookup against a pre-built name → discord_id map  (O(1) per word)
        2. Fuzzy fallback via difflib (cutoff=0.80) for near-exact mentions

        The 0.80 cutoff is intentionally strict here — false positives in text
        context injection are worse than false negatives. Explicit aliases set via
        /ghost set alias are caught in pass 1.

        Args:
            message:             Raw message text to scan.
            exclude_discord_id:  Sender's discord_id — excluded from results.

        Returns:
            List of discord_ids for users mentioned in the message.
        """
        from difflib import get_close_matches

        # Build candidate map: lowered_name → discord_id
        candidate_map: dict[str, str] = {}
        seen_obj_ids: set[int] = set()
        for state in self._users.values():
            if id(state) in seen_obj_ids or "discord" not in state.identifiers:
                continue
            seen_obj_ids.add(id(state))
            discord_id = state.identifiers["discord"].user_id
            if exclude_discord_id and discord_id == exclude_discord_id:
                continue
            for identity in state.identifiers.values():
                for field in (identity.username, identity.nickname, identity.display_name):
                    if field:
                        candidate_map[field.lower()] = discord_id
            for variant in state.name_variants:
                if variant:
                    candidate_map[variant] = discord_id
            for alias in state.aliases:
                if alias:
                    candidate_map[alias.lower()] = discord_id

        if not candidate_map:
            return []

        all_candidates = list(candidate_map.keys())

        # Extract words >= 4 chars, skipping common English words
        words = re.findall(r"\b\w{4,}\b", message.lower())
        words = [w for w in words if w not in _TEXT_SCAN_STOP_WORDS]

        found_ids: set[str] = set()
        fuzzy_queue: list[str] = []

        for word in words:
            if word in candidate_map:
                found_ids.add(candidate_map[word])
            else:
                fuzzy_queue.append(word)

        # Fuzzy pass — only on words that missed the exact scan
        for word in fuzzy_queue:
            matches = get_close_matches(word, all_candidates, n=1, cutoff=0.80)
            if matches:
                logger.debug(
                    "scan_message_for_users: fuzzy '%s' → '%s' (discord_id=%s)",
                    word, matches[0], candidate_map[matches[0]],
                )
                found_ids.add(candidate_map[matches[0]])

        return list(found_ids)

    # ------------------------------------------------------------------
    # Cone-related helpers (used by ConeManager)
    # ------------------------------------------------------------------

    def get_display_name(self, discord_id: str) -> str:
        """Return a human-readable name for a Discord ID, falling back gracefully."""
        discord_key = f"discord_{discord_id}"
        state = self._users.get(discord_key)
        if state and "discord" in state.identifiers:
            identity = state.identifiers["discord"]
            return identity.display_name or identity.nickname or identity.username
        return f"User{discord_id}"

    def find_discord_id_by_username(self, username: str) -> Optional[str]:
        """
        Look up a Discord ID by any known username/nickname/alias across all platforms.

        Resolution order:
        1. Exact match on username / nickname / display_name
        2. Match against stored name_variants (includes separator-split parts)
        3. Fuzzy match via difflib (cutoff=0.65) — catches partial names like 'goomber'
        """
        from difflib import get_close_matches

        username_lower = username.lower()

        # --- Pass 1: exact field match ---
        for state in self._users.values():
            for identity in state.identifiers.values():
                if (
                    identity.username.lower() == username_lower
                    or (identity.nickname and identity.nickname.lower() == username_lower)
                    or (identity.display_name and identity.display_name.lower() == username_lower)
                ):
                    if "discord" in state.identifiers:
                        return state.identifiers["discord"].user_id

        # --- Pass 2: name_variants + user-set aliases match ---
        seen_ids: set[int] = set()
        for state in self._users.values():
            if id(state) in seen_ids:
                continue
            seen_ids.add(id(state))
            all_variants = set(state.name_variants) | {a.lower() for a in state.aliases}
            if username_lower in all_variants and "discord" in state.identifiers:
                logger.debug(
                    "find_discord_id_by_username: variant/alias match '%s' → %s",
                    username, state.identifiers["discord"].user_id,
                )
                return state.identifiers["discord"].user_id

        # --- Pass 3: fuzzy fallback ---
        candidate_map: dict[str, str] = {}  # lowered_name → discord_id
        seen_ids2: set[int] = set()
        for state in self._users.values():
            if id(state) in seen_ids2 or "discord" not in state.identifiers:
                continue
            seen_ids2.add(id(state))
            discord_id = state.identifiers["discord"].user_id
            for identity in state.identifiers.values():
                for field in (identity.username, identity.nickname, identity.display_name):
                    if field:
                        candidate_map[field.lower()] = discord_id
            for variant in state.name_variants:
                if variant:
                    candidate_map[variant] = discord_id

        matches = get_close_matches(username_lower, list(candidate_map), n=1, cutoff=0.65)
        if matches:
            logger.debug(
                "find_discord_id_by_username: fuzzy match '%s' → '%s' (discord_id=%s)",
                username, matches[0], candidate_map[matches[0]],
            )
            return candidate_map[matches[0]]

        return None

    # ------------------------------------------------------------------
    # Special users (from special_users.json)
    # ------------------------------------------------------------------

    def load_special_users(self) -> dict:
        """Load static lore data for known users. Returns {} on failure."""
        candidates = [
            Path("special_users.json"),
            Path(__file__).resolve().parents[2] / "special_users.json",
        ]
        for path in candidates:
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, OSError) as exc:
                    logger.error("Failed to load special_users.json: %s", exc)
                    return {}
        logger.warning("special_users.json not found.")
        return {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_matching_user(self, username: str, nickname: Optional[str]) -> Optional[UserState]:
        search = {username.lower()}
        if nickname:
            search.add(nickname.lower())
        seen: set[int] = set()
        for state in self._users.values():
            if id(state) in seen:
                continue
            seen.add(id(state))
            for identity in state.identifiers.values():
                if (
                    identity.username.lower() in search
                    or (identity.nickname and identity.nickname.lower() in search)
                ):
                    return state
        return None

    def _relink_if_needed(self, state: UserState) -> None:
        """Ensure both discord_ and twitch_ keys point to the same object for linked accounts."""
        if "discord" in state.identifiers and "twitch" in state.identifiers:
            d_key = f"discord_{state.identifiers['discord'].user_id}"
            t_key = f"twitch_{state.identifiers['twitch'].user_id}"
            self._users[d_key] = state
            self._users[t_key] = state

    # ------------------------------------------------------------------
    # Persistence backends
    # ------------------------------------------------------------------

    async def _mongo_load(self) -> dict:
        database = _db_module.get_db()
        doc = await database.user_states.find_one({"_id": "current_states"})
        if doc:
            result = dict(doc)
            result.pop("_id", None)
            return result
        return {}

    async def _mongo_save(self, data: dict) -> None:
        database = _db_module.get_db()
        await database.user_states.find_one_and_replace(
            {"_id": "current_states"},
            {"_id": "current_states", **data},
            upsert=True,
        )

    def _file_load(self) -> dict:
        if not os.path.exists(_FALLBACK_FILE):
            return {}
        with open(_FALLBACK_FILE, encoding="utf-8") as f:
            return json.load(f)

    def _file_save(self, data: dict) -> None:
        import json as _json
        serialisable = _json.loads(_json.dumps(data, default=str))
        with open(_FALLBACK_FILE, "w", encoding="utf-8") as f:
            _json.dump(serialisable, f, indent=2)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _name_variants(username: str) -> list[str]:
    """Generate lowercase lookup variants for a username.

    Includes all parts produced by splitting on common separators so that
    e.g. 'Swastik Goomber' → ['swastik goomber', 'swastik', 'goomber'].
    """
    variants: set[str] = {username.lower()}
    for sep in (" ", ".", "_", "-"):
        if sep in username:
            for part in username.split(sep):
                if part:
                    variants.add(part.lower())
    return list(variants)


def _deserialise_user_state(data: dict) -> Optional[UserState]:
    """Convert a raw dict (from MongoDB / JSON) to a UserState. Returns None on failure."""
    try:
        # Normalise PlatformIdentity dicts
        identifiers_raw = data.get("identifiers", {})
        identifiers: dict[str, PlatformIdentity] = {}
        for platform, identity_dict in identifiers_raw.items():
            identifiers[platform] = PlatformIdentity(
                user_id=str(identity_dict.get("user_id", "")),
                username=identity_dict.get("username", ""),
                nickname=identity_dict.get("nickname"),
                display_name=identity_dict.get("display_name") or identity_dict.get("username", ""),
            )

        summaries_raw = data.get("summaries", {})
        summaries = UserSummaries(
            relationship=summaries_raw.get("relationship", "No additional information yet."),
            last_conversation=summaries_raw.get("last_conversation", "No conversation summary yet"),
            last_updated=datetime.fromisoformat(summaries_raw["last_updated"])
            if "last_updated" in summaries_raw
            else datetime.now(),
        )

        messages = []
        for msg in data.get("recent_messages", []):
            try:
                messages.append(
                    Message(
                        content=msg["content"],
                        from_bot=msg["from_bot"],
                        username=msg["username"],
                        timestamp=datetime.fromisoformat(msg["timestamp"])
                        if "timestamp" in msg
                        else datetime.now(),
                    )
                )
            except (KeyError, ValueError):
                continue

        last_interaction = data.get("last_interaction")
        if isinstance(last_interaction, str):
            last_interaction = datetime.fromisoformat(last_interaction)
        elif not isinstance(last_interaction, datetime):
            last_interaction = datetime.now()

        primary_name = data.get("username") or data.get("primary_name", "unknown")
        name_variants = data.get("name_variants") or _name_variants(primary_name)

        return UserState(
            identifiers=identifiers,
            primary_name=primary_name,
            name_variants=name_variants,
            summaries=summaries,
            recent_messages=messages,
            last_interaction=last_interaction,
        )
    except Exception as exc:
        logger.error("Failed to deserialise UserState: %s — data: %s", exc, data)
        return None


def _parse_summary_response(response_text: str) -> tuple[str, str]:
    """Extract [RELATIONSHIP_SUMMARY] and [CONVERSATION_SUMMARY] sections."""
    relationship = ""
    conversation = ""

    sections = response_text.split("[")
    for section in sections:
        if "RELATIONSHIP_SUMMARY]" in section:
            relationship = section.split("]", 1)[1].strip()
        elif "CONVERSATION_SUMMARY]" in section:
            conversation = section.split("]", 1)[1].strip()

    return relationship, conversation
