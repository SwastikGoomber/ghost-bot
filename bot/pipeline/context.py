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


def _load_persona() -> str:
    global _persona_cache
    if _persona_cache is not None:
        return _persona_cache
    candidates = [
        Path("prompts/persona.md"),
        Path(__file__).resolve().parents[2] / "prompts" / "persona.md",
    ]
    for path in candidates:
        if path.exists():
            _persona_cache = path.read_text(encoding="utf-8").strip()
            return _persona_cache
    logger.error("persona.md not found — using empty persona.")
    _persona_cache = ""
    return _persona_cache


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
    ) -> str:
        """
        Assemble the full system prompt.

        Args:
            user_state:            State of the user who sent the message.
            platform:              Platform (DISCORD or TWITCH).
            current_message:       The raw message text.
            mentioned_user_states: [(username, UserState), …] for users mentioned in the message.

        Returns:
            A single system prompt string ready to pass to LLMClient.generate().
        """
        parts: list[str] = []

        # 1. Core persona
        parts.append(_load_persona())

        # 2. Hard character rule (never breaks in any context)
        parts.append(
            "CRITICAL: Never acknowledge being an AI or break character. "
            "Always respond as Ghost, the teenage dragon."
        )

        # 3. Platform constraint
        if platform == Platform.TWITCH:
            parts.append(
                "IMPORTANT: Keep your responses under 500 characters for Twitch chat. "
                "You can think longer thoughts, but your direct replies must be concise."
            )

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

        return "\n\n".join(filter(None, parts))

    def _build_user_context_block(
        self, username: str, state: UserState, *, is_sender: bool
    ) -> str:
        lines: list[str] = []
        role_label = "CURRENT SPEAKER" if is_sender else "MENTIONED USER"
        lines.append(f"{role_label}: {username}")

        # Special lore data
        primary_name = self._variant_lookup.get(username)
        if primary_name and primary_name in self._special_users:
            user_data = self._special_users[primary_name]
            lines.append(f"ROLE: {user_data.get('role', '')}")
            lines.append(f"CONTEXT: {user_data.get('context', '')}")
            aliases = [v for v in user_data.get("variants", []) if v.lower() != username]
            if aliases:
                lines.append(f"ALSO KNOWN AS: {', '.join(aliases)}")

        # Relationship summary
        if state.summaries.relationship and \
                state.summaries.relationship != "No additional information yet.":
            lines.append(f"RELATIONSHIP WITH GHOST: {state.summaries.relationship}")

        # Conversation summary for mentioned users only (avoid duplication for sender)
        if not is_sender and state.summaries.last_conversation and \
                state.summaries.last_conversation != "No conversation summary yet":
            lines.append(f"RECENT INTERACTIONS WITH GHOST: {state.summaries.last_conversation}")

        return "\n".join(lines)

    def extract_mentioned_usernames(self, message: str) -> list[str]:
        """Return special-user primary names mentioned in the message."""
        found: set[str] = set()
        message_lower = message.lower()
        words = re.findall(r"@?\w+", message_lower)
        for word in words:
            word = word.lstrip("@").strip()
            if word in self._variant_lookup:
                found.add(self._variant_lookup[word])
        return list(found)
