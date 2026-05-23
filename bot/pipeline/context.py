"""
ContextBuilder — assembles the system prompt for each LLM call.

It is the only place that reads from UserState and special_users.json to
build a system prompt string. The handler and platform layers never touch
prompt strings directly.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from ..utils.models import Platform, UserState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persona loading (cached at class level)
# ---------------------------------------------------------------------------

_persona_cache: Optional[str] = None
_anti_repetition_template_cache: Optional[str] = None
_cone_hint_cache: Optional[str] = None
_cone_hint_repetition_cache: Optional[str] = None
_platform_twitch_cache: Optional[str] = None


def _load_prompt(filename: str, cache_attr: str) -> str:
    """Generic cached prompt loader from prompts/ directory."""
    global _anti_repetition_template_cache, _cone_hint_cache, _cone_hint_repetition_cache, _platform_twitch_cache
    candidates = [
        Path(f"prompts/{filename}"),
        Path(__file__).resolve().parents[2] / "prompts" / filename,
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    logger.error("%s not found — returning empty string.", filename)
    return ""


def _load_persona() -> str:
    global _persona_cache
    if _persona_cache is not None:
        return _persona_cache
    _persona_cache = _load_prompt("persona.md", "_persona_cache")
    return _persona_cache


def _load_anti_repetition_template() -> str:
    global _anti_repetition_template_cache
    if _anti_repetition_template_cache is None:
        _anti_repetition_template_cache = _load_prompt("anti_repetition.md", "_anti_repetition_template_cache")
    return _anti_repetition_template_cache


def _load_cone_hint() -> str:
    global _cone_hint_cache
    if _cone_hint_cache is None:
        _cone_hint_cache = _load_prompt("cone_hint.md", "_cone_hint_cache")
    return _cone_hint_cache


def _load_cone_hint_repetition() -> str:
    global _cone_hint_repetition_cache
    if _cone_hint_repetition_cache is None:
        _cone_hint_repetition_cache = _load_prompt("cone_hint_repetition.md", "_cone_hint_repetition_cache")
    return _cone_hint_repetition_cache


def _load_platform_twitch() -> str:
    global _platform_twitch_cache
    if _platform_twitch_cache is None:
        _platform_twitch_cache = _load_prompt("platform_twitch.md", "_platform_twitch_cache")
    return _platform_twitch_cache


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

class ContextBuilder:
    """Builds the system prompt for a single message exchange."""

    def __init__(self, special_users: dict) -> None:
        self._special_users = special_users
        # Build a variant → primary_name lookup
        self._variant_lookup: dict[str, str] = {}
        for primary, data in special_users.items():
            for variant in data.get("variants", []):
                self._variant_lookup[variant.lower().strip()] = primary

    def build_system_prompt(
        self,
        user_state: UserState,
        platform: Platform,
        current_message: str,
        mentioned_user_states: Optional[list[tuple[str, UserState]]] = None,
        rag_context: Optional[str] = None,
        cone_requested: bool = False,
    ) -> str:
        """
        Assemble the full system prompt.

        Args:
            user_state:            State of the user who sent the message.
            platform:              Platform (DISCORD or TWITCH).
            current_message:       The raw message text.
            mentioned_user_states: [(username, UserState), …] for users mentioned in the message.
            rag_context:           Pre-formatted retrieved memory block (from RAG retriever).
            cone_requested:        True if the router detected an explicit cone request.

        Returns:
            A single system prompt string ready to pass to LLMClient.generate().
        """
        parts: list[str] = []

        # 1. Core persona (includes CRITICAL character rule at the end of persona.md)
        parts.append(_load_persona())

        # 2. Platform constraint
        if platform == Platform.TWITCH:
            parts.append(_load_platform_twitch())

        # 4. Sender context
        sender_username = user_state.primary_identity.username.lower()
        parts.append(self._build_user_context_block(sender_username, user_state, is_sender=True))

        # 5. Mentioned users context
        if mentioned_user_states:
            for mention_username, mention_state in mentioned_user_states:
                block = self._build_user_context_block(mention_username, mention_state, is_sender=False)
                if block:
                    parts.append(block)

        # 6. Recent conversation summary for the sender
        if user_state.summaries.last_conversation and \
                user_state.summaries.last_conversation != "No conversation summary yet":
            parts.append(
                f"RECENT CONVERSATION CONTEXT: {user_state.summaries.last_conversation}"
            )

        # 7. RAG retrieved memory (if available)
        if rag_context:
            parts.append(rag_context)

        # 8. Global anti-repetition guard — fires on every turn when Ghost has
        #    said 2+ things recently. Prevents phrase loops even on plain chat.
        recent_bot = [
            msg.content for msg in user_state.recent_messages
            if msg.from_bot and msg.content.strip()
        ][-4:]
        if len(recent_bot) >= 2:
            recent_lines = "\n".join(f'  - "{m}"' for m in recent_bot)
            template = _load_anti_repetition_template()
            parts.append(template.replace("{recent_messages}", recent_lines))

        # 9. Cone request hint + cone-response variety reminder
        if cone_requested:
            parts.append(_load_cone_hint())
            if recent_bot:
                parts.append(_load_cone_hint_repetition())

        return "\n\n".join(filter(None, parts))

    def _build_user_context_block(
        self, username: str, state: UserState, *, is_sender: bool
    ) -> str:
        lines: list[str] = []
        role_label = "CURRENT SPEAKER" if is_sender else "MENTIONED USER"
        lines.append(f"{role_label}: {username}")

        # Special lore data (from special_users.json, legacy)
        primary_name = self._variant_lookup.get(username)
        if primary_name and primary_name in self._special_users:
            user_data = self._special_users[primary_name]
            lines.append(f"ROLE: {user_data.get('role', '')}")
            lines.append(f"CONTEXT: {user_data.get('context', '')}")
            lore_aliases = [v for v in user_data.get("variants", []) if v.lower() != username]
            if lore_aliases:
                lines.append(f"ALSO KNOWN AS: {', '.join(lore_aliases)}")

        # User-set profile (aliases, pronouns, bio)
        if state.aliases:
            lines.append(f"ALIASES: {', '.join(state.aliases)}")
        if state.pronouns:
            lines.append(f"PRONOUNS: {', '.join(state.pronouns)}")
        if state.bio:
            lines.append(f"BIO: {state.bio}")

        # Relationship summary
        if state.summaries.relationship and \
                state.summaries.relationship != "No additional information yet.":
            lines.append(f"RELATIONSHIP WITH GHOST: {state.summaries.relationship}")

        # For mentioned users (not the sender): add last conversation summary + last 6 messages
        if not is_sender:
            if state.summaries.last_conversation and \
                    state.summaries.last_conversation != "No conversation summary yet":
                lines.append(f"RECENT INTERACTIONS WITH GHOST: {state.summaries.last_conversation}")

            recent = state.recent_messages[-6:]
            if recent:
                lines.append("THEIR RECENT MESSAGES:")
                for msg in recent:
                    speaker = "Ghost" if msg.from_bot else msg.username
                    lines.append(f"  {speaker}: {msg.content}")

        return "\n".join(lines)

    def extract_mentioned_usernames(self, message: str) -> list[str]:
        """
        Return names/IDs that refer to users mentioned in the message.

        Returns a mix of:
        - Special-user variant names (from special_users.json lookup)
        - Raw numeric Discord IDs extracted from <@ID> and <@!ID> mention syntax

        The caller is responsible for resolving each entry to a UserState via
        state_manager.find_discord_id_by_username().
        """
        found: set[str] = set()

        # Raw @mention syntax → return the numeric ID so handler can resolve directly
        for match in re.finditer(r"<@!?(\d+)>", message):
            found.add(match.group(1))  # numeric discord ID string

        # Text-based special-user variant scan
        message_lower = message.lower()
        words = re.findall(r"@?\w+", message_lower)
        for word in words:
            word = word.lstrip("@").strip()
            if word in self._variant_lookup:
                found.add(self._variant_lookup[word])

        return list(found)
