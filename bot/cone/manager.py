"""
ConeManager — all cone state operations in one place.

Design decisions:
- Every public method is async and always returns a ConeResult (never a raw string).
- Cone data is keyed by Discord ID (a numeric string). This is the stable identifier.
- ConeManager holds a reference to StateManager so it can persist changes immediately.
- apply() and remove() are the only two mutation methods; all others are read-only.
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Optional

from bot.utils.exceptions import ConeEffectNotFoundError
from bot.utils.models import ConeCondition, ConeData, ConeResult
from bot.cone.registry import resolve as resolve_effect

if TYPE_CHECKING:
    from ..memory.state import StateManager

logger = logging.getLogger(__name__)


class ConeManager:
    def __init__(self, state_manager: "StateManager") -> None:
        self._state = state_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def apply(
        self,
        discord_id: str,
        effect: str,
        *,
        applied_by: str,
        reason: str = "no reason given",
        duration: Optional[str] = None,
        condition: Optional[str] = None,
    ) -> ConeResult:
        """
        Cone a user.

        Args:
            discord_id: Target user's Discord ID (numeric string).
            effect:     Effect name (canonical or alias — resolved automatically).
            applied_by: Username of the person applying the cone.
            reason:     Why the cone is being applied.
            duration:   Human-readable duration ("10 minutes", "2 hours", etc.) or None for permanent.
            condition:  Human-readable release condition ("until they say sorry", etc.) or None.

        Returns:
            ConeResult with success=True on success, success=False with a descriptive message on failure.
        """
        try:
            canonical_effect = resolve_effect(effect)
        except ConeEffectNotFoundError as exc:
            return ConeResult(success=False, message=str(exc))

        duration_seconds = _parse_duration(duration)
        condition_data = _parse_condition(condition)

        current_time = time.time()
        expiry_time = current_time + duration_seconds if duration_seconds > 0 else None

        # Build the display name for responses
        display_name = self._state.get_display_name(discord_id)

        # Override any existing cone
        existing = self._state.cone_data.get(discord_id)
        override_msg = ""
        if existing and existing.active:
            override_msg = f" (overriding previous '{existing.effect}' effect)"

        self._state.cone_data[discord_id] = ConeData(
            effect=canonical_effect,
            active=True,
            applied_by=applied_by,
            reason=reason,
            timestamp=current_time,
            expiry_time=expiry_time,
            condition=condition_data,
            duration_str=duration or "permanent",
            target_username=display_name,
        )

        await self._state.save_states()

        duration_text = f" for {duration}" if duration else " permanently"
        condition_text = _format_condition_text(condition_data, condition)

        logger.info(
            "Coned %s (ID: %s) with '%s' by %s%s",
            display_name, discord_id, canonical_effect, applied_by, override_msg,
        )
        return ConeResult(
            success=True,
            message=(
                f"✅ Successfully coned {display_name} with '{canonical_effect}' effect"
                f"{duration_text}{condition_text}! Reason: {reason}{override_msg}"
            ),
        )

    async def remove(self, discord_id: str, *, removed_by: str) -> ConeResult:
        """
        Remove a cone from a user.

        Args:
            discord_id: Target user's Discord ID.
            removed_by: Username of the person removing the cone.

        Returns:
            ConeResult with success=True if the cone was active and has been removed.
        """
        existing = self._state.cone_data.get(discord_id)
        display_name = self._state.get_display_name(discord_id)

        if not existing or not existing.active:
            return ConeResult(
                success=False,
                message=f"❌ {display_name} is not currently coned.",
            )

        effect = existing.effect
        existing.active = False
        existing.unconed_by = removed_by
        existing.unconed_at = time.time()

        await self._state.save_states()

        logger.info("Unconed %s (ID: %s, was '%s') by %s", display_name, discord_id, effect, removed_by)
        return ConeResult(
            success=True,
            message=f"✅ Successfully unconed {display_name} (removed '{effect}' effect)!",
        )

    async def is_coned(self, discord_id: str) -> tuple[bool, Optional[str]]:
        """
        Check whether a user is actively coned.

        Returns:
            (True, effect_name) if coned, (False, None) otherwise.
            Automatically expires timed cones.
        """
        data = self._state.cone_data.get(discord_id)
        if not data or not data.active:
            return False, None

        if data.expiry_time and time.time() > data.expiry_time:
            data.active = False
            data.expired_at = time.time()
            await self._state.save_states()
            logger.info("Cone for %s expired.", discord_id)
            return False, None

        return True, data.effect

    async def check_and_release_condition(self, discord_id: str, message_content: str) -> bool:
        """
        Check whether a cone's release condition has been met.

        Mutates the cone record and persists if the condition is satisfied.

        Returns:
            True if the condition was met and the cone has been released.
        """
        data = self._state.cone_data.get(discord_id)
        if not data or not data.active or not data.condition:
            return False

        if _condition_met(data.condition, message_content):
            data.active = False
            data.condition_met_at = time.time()
            await self._state.save_states()
            logger.info("Cone condition met for %s — cone released.", discord_id)
            return True

        return False

    def get_status(self, discord_id: str) -> ConeResult:
        """
        Return a human-readable status for a user's current cone state.
        Does NOT mutate anything (synchronous, no persistence).
        """
        data = self._state.cone_data.get(discord_id)
        display_name = self._state.get_display_name(discord_id)

        if not data:
            return ConeResult(success=False, message=f"{display_name} has never been coned.")

        if not data.active:
            if data.unconed_by:
                reason = f"unconed by {data.unconed_by}"
            elif data.expired_at:
                reason = "cone expired"
            elif data.condition_met_at:
                reason = "cone condition was met"
            else:
                reason = "not currently coned"
            return ConeResult(success=False, message=f"{display_name} is not coned ({reason}).")

        # Remaining time
        remaining_text = ""
        if data.expiry_time:
            remaining_seconds = int(data.expiry_time - time.time())
            if remaining_seconds > 3600:
                remaining_text = f" ({remaining_seconds // 3600}h remaining)"
            elif remaining_seconds > 60:
                remaining_text = f" ({remaining_seconds // 60}m remaining)"
            elif remaining_seconds > 0:
                remaining_text = f" ({remaining_seconds}s remaining)"
            else:
                remaining_text = " (expired)"

        condition_text = ""
        if data.condition and data.condition.type == "say_word":
            condition_text = f" until they say '{data.condition.word}'"

        return ConeResult(
            success=True,
            message=(
                f"{display_name} is coned with '{data.effect}' by {data.applied_by} "
                f"({data.duration_str}{remaining_text}{condition_text}). "
                f"Reason: {data.reason}"
            ),
        )

    def find_discord_id_by_username(self, username: str) -> Optional[str]:
        """
        Resolve a username or Discord mention to a Discord ID using the state manager.
        Returns None if the user cannot be found.
        """
        # Handle Discord mention format: <@123456789> or <@!123456789>
        mention_match = re.match(r"<@!?(\d+)>", username.strip())
        if mention_match:
            return mention_match.group(1)

        # Numeric string — treat as Discord ID directly
        if username.strip().isdigit():
            return username.strip()

        # Lookup by username in state manager
        return self._state.find_discord_id_by_username(username)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_duration(duration_str: Optional[str]) -> int:
    """Parse a human-readable duration to seconds. Returns 0 for permanent."""
    if not duration_str:
        return 0
    lower = duration_str.lower().strip()
    if lower in ("permanent", "forever", "indefinite", ""):
        return 0

    match = re.search(r"(\d+)\s*(second|minute|hour|day|week)s?", lower)
    if not match:
        return 0

    number = int(match.group(1))
    unit = match.group(2)
    multipliers = {
        "second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800,
    }
    return number * multipliers.get(unit, 0)


def _parse_condition(condition_str: Optional[str]) -> Optional[ConeCondition]:
    """Parse a human-readable release condition."""
    if not condition_str:
        return None

    lower = condition_str.lower().strip()

    if "say sorry" in lower or "apologize" in lower or "apologise" in lower:
        return ConeCondition(type="say_word", word="sorry", variants=["sorry", "apologize", "apologise", "apologies"])
    if "say please" in lower:
        return ConeCondition(type="say_word", word="please", variants=["please"])
    if "say" in lower:
        # Extract the word they need to say
        word = lower.replace("until they say", "").replace("say", "").strip().strip("\"'")
        if word:
            return ConeCondition(type="say_word", word=word, variants=[word])

    return None


def _condition_met(condition: ConeCondition, message_content: str) -> bool:
    lower_content = message_content.lower()
    return any(variant in lower_content for variant in condition.variants)


def _format_condition_text(condition_data: Optional[ConeCondition], raw_condition: Optional[str]) -> str:
    if condition_data and condition_data.type == "say_word":
        return f" until they say '{condition_data.word}'"
    if raw_condition:
        raw = raw_condition.strip()
        return f" {raw}" if raw.startswith("until") else f" until they {raw}"
    return ""
