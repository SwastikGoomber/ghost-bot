"""
Cone approval pipeline — two-tier gate between Gemini's cone intent and ConeManager.

Tier 0 — Programmatic gate (~1ms, no LLM):
    - Target already coned? → reject
    - Target coned in the last N minutes? → reject
    - Hourly total exceeded? → reject
    - Authorized user requested? → passing to approval agent with leniency (skip Tier 1 evaluation strictness)

Tier 1 — Gemma 4 Approval Agent (~150ms, only for unapproved / autonomous):
    - Receives conversation context + trigger type + relationship summary
    - Applies tiered strictness: autonomous is much harder to approve than requested
    - Outputs ConeApprovalResult(approved, reason)

The result of run_cone_approval() is always ConeApprovalResult.
The caller (handler.py) decides what to do with it.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from bot.utils.config import get_config
from bot.utils.exceptions import LLMError
from bot.utils.llm import get_llm_client
from bot.utils.llm.ollama import OllamaClient
from bot.utils.models import ConeApprovalResult, Message, UserState, ConeData

if TYPE_CHECKING:
    from bot.cone.manager import ConeManager

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "cone_approval.md"
_APPROVAL_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")

_UNCONE_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "uncone_approval.md"
_UNCONE_PROMPT_TEMPLATE = _UNCONE_PROMPT_PATH.read_text(encoding="utf-8")


def format_elapsed_time(seconds: float) -> str:
    """Format elapsed time in seconds into a human-readable string."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    minutes = int(seconds // 60)
    if minutes < 60:
        remaining_seconds = int(seconds % 60)
        return f"{minutes} minutes, {remaining_seconds} seconds"
    hours = int(minutes // 60)
    remaining_minutes = int(minutes % 60)
    return f"{hours} hours, {remaining_minutes} minutes"

# In-process rolling history for the Tier 0 rate limits.
# {target_username: [datetime_of_cone, ...]}
_cone_history: dict[str, list[datetime]] = {}
# Track autonomous cones per day {date_str: count}
_autonomous_today: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Tier 0 — Programmatic gate
# ---------------------------------------------------------------------------

class ProgrammaticGateResult:
    """Internal result of the programmatic gate check."""
    def __init__(
        self,
        passed: bool,
        instant_approve: bool = False,
        reject_reason: str = "",
    ) -> None:
        self.passed = passed
        self.instant_approve = instant_approve  # True = bypass Tier 1 entirely
        self.reject_reason = reject_reason


async def programmatic_gate(
    cone_target: str,
    cone_trigger: str,
    requester_username: str,
    cone_manager: "ConeManager",
) -> ProgrammaticGateResult:
    """
    Fast, synchronous gate that runs before the LLM approval agent.

    Args:
        cone_target:        Username of the person to be coned.
        cone_trigger:       "requested_approved" | "requested_unapproved" | "autonomous"
        requester_username: Username of the person who triggered/requested the cone.
        cone_manager:       Active ConeManager instance (for active cone check).

    Returns:
        ProgrammaticGateResult indicating pass/reject/instant-approve.
    """
    cfg = get_config()
    now = datetime.now(timezone.utc)

    # Check 1: is the target currently coned?
    target_discord_id = cone_manager.find_discord_id_by_username(cone_target)
    if target_discord_id:
        is_active, _ = await cone_manager.is_coned(target_discord_id)
        if is_active:
            logger.debug("Gate: %s is already coned — rejecting.", cone_target)
            return ProgrammaticGateResult(
                passed=False,
                reject_reason=f"{cone_target} is already coned.",
            )
    else:
        logger.debug("Gate: could not resolve '%s' to a discord_id — skipping active cone check.", cone_target)

    # Check 2: per-target cooldown
    cooldown_minutes = cfg.cone.per_target_cooldown_minutes
    cooldown_cutoff = now - timedelta(minutes=cooldown_minutes)
    recent_for_target = [
        t for t in _cone_history.get(cone_target, [])
        if t > cooldown_cutoff
    ]
    if recent_for_target:
        logger.debug(
            "Gate: %s was coned recently (cooldown %dm) — rejecting.",
            cone_target, cooldown_minutes,
        )
        return ProgrammaticGateResult(
            passed=False,
            reject_reason=f"{cone_target} was coned in the last {cooldown_minutes} minutes.",
        )

    # Check 3: hourly total across all targets
    hourly_cutoff = now - timedelta(hours=1)
    total_hourly = sum(
        len([t for t in times if t > hourly_cutoff])
        for times in _cone_history.values()
    )
    if total_hourly >= cfg.cone.hourly_limit:
        logger.debug(
            "Gate: hourly limit %d reached (%d in last hour) — rejecting.",
            cfg.cone.hourly_limit, total_hourly,
        )
        return ProgrammaticGateResult(
            passed=False,
            reject_reason=f"Hourly cone limit ({cfg.cone.hourly_limit}) reached.",
        )

    # Check 4: autonomous daily cap
    if cone_trigger == "autonomous":
        today = now.strftime("%Y-%m-%d")
        auto_count = _autonomous_today.get(today, 0)
        if auto_count >= cfg.cone.autonomous_max_per_day:
            logger.debug(
                "Gate: autonomous daily limit %d reached — rejecting.",
                cfg.cone.autonomous_max_per_day,
            )
            return ProgrammaticGateResult(
                passed=False,
                reject_reason=f"Autonomous cone daily limit ({cfg.cone.autonomous_max_per_day}) reached.",
            )

    # Check 5: permitted (authorized) users who explicitly requested → still go through the agent,
    # but the prompt treats them leniently since Ghost actually trusts them
    if cone_trigger == "requested_approved":
        requester_lower = requester_username.lower()
        if requester_lower in cfg.cone.permissions:
            logger.debug(
                "Gate: authorized user %s — passing to approval agent with leniency.",
                requester_lower,
            )
            return ProgrammaticGateResult(passed=True)

    return ProgrammaticGateResult(passed=True)


def record_cone_applied(cone_target: str, cone_trigger: str) -> None:
    """
    Record a successfully applied cone into the in-process history.

    Call this after ConeManager.apply() succeeds.
    """
    now = datetime.now(timezone.utc)
    if cone_target not in _cone_history:
        _cone_history[cone_target] = []
    _cone_history[cone_target].append(now)

    if cone_trigger == "autonomous":
        today = now.strftime("%Y-%m-%d")
        _autonomous_today[today] = _autonomous_today.get(today, 0) + 1

    # Prune old history (keep only last 24h to avoid memory growth)
    cutoff = now - timedelta(hours=24)
    for target in list(_cone_history.keys()):
        _cone_history[target] = [t for t in _cone_history[target] if t > cutoff]
        if not _cone_history[target]:
            del _cone_history[target]


# ---------------------------------------------------------------------------
# Tier 1 — Approval Agent (Gemma 4 via Ollama)
# ---------------------------------------------------------------------------

async def approval_agent(
    cone_target: str,
    cone_trigger: str,
    cone_effect: str,
    recent_messages: list[Message],
    requester_state: Optional[UserState],
    is_requester_authorized: bool = False,
) -> ConeApprovalResult:
    """
    Ask Gemma 4 whether this cone should be approved.

    Only called after Tier 0 passes AND the trigger is not "requested_approved".

    Args:
        cone_target:             Who is being coned.
        cone_trigger:            "requested_unapproved" | "autonomous"
        cone_effect:             Effect name (e.g. "uwu").
        recent_messages:         Last 5 messages from the conversation.
        requester_state:         UserState of the requester (if known, else None).
        is_requester_authorized: Whether the requester is on the official permissions list.

    Returns:
        ConeApprovalResult(approved, reason).
    """
    client = get_llm_client("cone_approval")
    if client is None:
        logger.error("Cone approval client is not available — denying by default.")
        return ConeApprovalResult(approved=False, reason="Approval client unavailable.")

    # Build context string from recent messages
    ctx_lines = []
    for msg in recent_messages[-5:]:
        speaker = "Ghost" if msg.from_bot else msg.username or "User"
        ctx_lines.append(f"{speaker}: {msg.content}")
    conversation_context = "\n".join(ctx_lines) if ctx_lines else "(no recent context)"

    # Relationship summary for the requester
    relationship_summary = "(unknown user — no relationship data)"
    if requester_state and requester_state.summaries and requester_state.summaries.relationship:
        relationship_summary = requester_state.summaries.relationship

    # Cone history summary (last hour)
    now = datetime.now(timezone.utc)
    hourly_cutoff = now - timedelta(hours=1)
    total_hourly = sum(
        len([t for t in times if t > hourly_cutoff])
        for times in _cone_history.values()
    )
    today = now.strftime("%Y-%m-%d")
    auto_today = _autonomous_today.get(today, 0)
    cone_history_summary = (
        f"{total_hourly} cones applied in the last hour. "
        f"{auto_today} autonomous cones today."
    )

    user_content = (
        "## Case Context for Decision:\n\n"
        f"- **Target:** {cone_target}\n"
        f"- **Trigger type:** {cone_trigger}\n"
        f"- **Requested effect:** {cone_effect}\n"
        f"- **Requester is authorized user:** {'Yes' if is_requester_authorized else 'No'}\n"
        f"- **Requester relationship summary:** {relationship_summary}\n"
        f"- **Recent cone history:** {cone_history_summary}\n\n"
        "### Recent Conversation Context:\n"
        f"{conversation_context}\n\n"
        "### Decision Request:\n"
        f"Should we approve coning {cone_target} with {cone_effect}? Output only the JSON response matching the schema."
    )

    try:
        raw = await client.generate_json(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=_APPROVAL_PROMPT_TEMPLATE,
        )
        
        cleaned_raw = raw.strip()
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_raw, re.DOTALL)
        if json_match:
            cleaned_raw = json_match.group(1).strip()
        elif not cleaned_raw.startswith("{") and "{" in cleaned_raw:
            start = cleaned_raw.find("{")
            end = cleaned_raw.rfind("}")
            if start != -1 and end != -1:
                cleaned_raw = cleaned_raw[start:end+1]

        if not cleaned_raw:
            logger.warning("Approval agent received empty response from Ollama — denying by default.")
            return ConeApprovalResult(approved=False, reason="Empty response from approval agent.")

        data = json.loads(cleaned_raw)
        result = ConeApprovalResult(
            approved=bool(data.get("approved", False)),
            reason=str(data.get("reason", "")),
        )
        logger.info(
            "Cone approval [%s → %s via %s]: approved=%s — %s",
            cone_effect, cone_target, cone_trigger, result.approved, result.reason,
        )
        return result

    except json.JSONDecodeError as exc:
        logger.warning("Approval agent JSON parse failed. Raw output: %r. Error: %s", raw, exc)
        return ConeApprovalResult(approved=False, reason="JSON parse failed.")
    except LLMError as exc:
        logger.warning("Approval agent failed (%s) — denying by default.", exc)
        return ConeApprovalResult(
            approved=False,
            reason=f"Approval agent error: {exc}",
        )


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------

async def run_cone_approval(
    cone_target: str,
    cone_trigger: str,
    cone_effect: str,
    requester_username: str,
    recent_messages: list[Message],
    requester_state: Optional[UserState],
    cone_manager: "ConeManager",
) -> ConeApprovalResult:
    """
    Run the full two-tier cone approval pipeline.

    Returns ConeApprovalResult. If approved=True, the caller must also call
    record_cone_applied() after ConeManager.apply() succeeds.

    Args:
        cone_target:        Username of the person to be coned.
        cone_trigger:       "requested_approved" | "requested_unapproved" | "autonomous"
        cone_effect:        Cone effect name.
        requester_username: Username of whoever sent the message.
        recent_messages:    Last N messages (for approval agent context).
        requester_state:    UserState of the requester (for relationship context).
        cone_manager:       Active ConeManager for active-cone checks.
    """
    # Tier 0
    gate = await programmatic_gate(
        cone_target=cone_target,
        cone_trigger=cone_trigger,
        requester_username=requester_username,
        cone_manager=cone_manager,
    )

    if not gate.passed:
        return ConeApprovalResult(approved=False, reason=gate.reject_reason)

    if gate.instant_approve:
        return ConeApprovalResult(approved=True, reason="Instant approve — authorized user request.")

    # Tier 1
    cfg = get_config()
    is_requester_authorized = requester_username.lower() in cfg.cone.permissions
    return await approval_agent(
        cone_target=cone_target,
        cone_trigger=cone_trigger,
        cone_effect=cone_effect,
        recent_messages=recent_messages,
        requester_state=requester_state,
        is_requester_authorized=is_requester_authorized,
    )


# ---------------------------------------------------------------------------
# Uncone approval pipeline — programmatic + Gemma 4 gate
# ---------------------------------------------------------------------------

async def run_uncone_approval(
    cone_target: str,
    requester_username: str,
    recent_messages: list[Message],
    requester_state: Optional[UserState],
    cone_manager: "ConeManager",
) -> ConeApprovalResult:
    """
    Run the full uncone approval pipeline.

    Args:
        cone_target:        Username of the person to be unconed.
        requester_username: Username of whoever sent the message.
        recent_messages:    Last N messages (for approval agent context).
        requester_state:    UserState of the requester (for relationship context).
        cone_manager:       Active ConeManager for active-cone checks.
    """
    # Tier 0 programmatic gate
    target_discord_id = cone_manager.find_discord_id_by_username(cone_target)
    if not target_discord_id:
        logger.debug("Uncone Gate: could not resolve '%s' to a discord_id", cone_target)
        return ConeApprovalResult(
            approved=False,
            reason=f"Could not resolve uncone target '{cone_target}' to a Discord ID.",
        )

    is_active, _ = await cone_manager.is_coned(target_discord_id)
    if not is_active:
        logger.debug("Uncone Gate: %s is not currently coned", cone_target)
        return ConeApprovalResult(
            approved=False,
            reason=f"{cone_target} is not currently coned.",
        )

    active_cone = cone_manager._state.cone_data.get(target_discord_id)
    if not active_cone or not active_cone.active:
        logger.debug("Uncone Gate: no active cone record for %s", cone_target)
        return ConeApprovalResult(
            approved=False,
            reason=f"{cone_target} is not currently coned.",
        )

    # Tier 1 Ollama/Gemma agent evaluation
    cfg = get_config()
    is_requester_authorized = requester_username.lower() in cfg.cone.permissions

    return await uncone_approval_agent(
        cone_target=cone_target,
        active_cone=active_cone,
        requester_username=requester_username,
        is_requester_authorized=is_requester_authorized,
        recent_messages=recent_messages,
        requester_state=requester_state,
    )


async def uncone_approval_agent(
    cone_target: str,
    active_cone: ConeData,
    requester_username: str,
    is_requester_authorized: bool,
    recent_messages: list[Message],
    requester_state: Optional[UserState],
) -> ConeApprovalResult:
    """
    Ask Gemma 4 whether this uncone should be approved using the uncone_approval.md template.
    """
    import time
    from bot.utils.llm import get_llm_client
    from bot.utils.llm.ollama import OllamaClient

    client = get_llm_client("cone_approval")
    if client is None:
        logger.error("Cone approval client is not available — denying by default.")
        return ConeApprovalResult(approved=False, reason="Approval client unavailable.")

    # Format recent conversation context
    ctx_lines = []
    for msg in recent_messages[-5:]:
        speaker = "Ghost" if msg.from_bot else msg.username or "User"
        ctx_lines.append(f"{speaker}: {msg.content}")
    conversation_context = "\n".join(ctx_lines) if ctx_lines else "(no recent context)"

    # Format relationship summary
    relationship_summary = "(unknown user — no relationship data)"
    if requester_state and requester_state.summaries and requester_state.summaries.relationship:
        relationship_summary = requester_state.summaries.relationship

    # Calculate time elapsed
    elapsed_seconds = max(0.0, time.time() - active_cone.timestamp)
    time_elapsed_str = format_elapsed_time(elapsed_seconds)

    # Build prompt
    user_content = (
        "## Case Context for Decision:\n\n"
        "### Active Cone Details\n"
        f"- **Target:** {cone_target}\n"
        f"- **Current effect:** {active_cone.effect}\n"
        f"- **Applied by:** {active_cone.applied_by}\n"
        f"- **Original reason/trigger:** {active_cone.reason}\n"
        f"- **Original reason text:** {active_cone.reason}\n"
        f"- **Time elapsed since coned:** {time_elapsed_str}\n\n"
        "### Uncone Request Details\n"
        f"- **Requester:** {requester_username}\n"
        f"- **Requester is authorized user:** {'Yes' if is_requester_authorized else 'No'}\n"
        f"- **Requester relationship summary:** {relationship_summary}\n\n"
        "### Recent Conversation Context:\n"
        f"{conversation_context}\n\n"
        "### Decision Request:\n"
        f"Should we approve removing the cone from {cone_target}? Output only the JSON response matching the schema."
    )

    try:
        raw = await client.generate_json(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=_UNCONE_PROMPT_TEMPLATE,
        )

        cleaned_raw = raw.strip()
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_raw, re.DOTALL)
        if json_match:
            cleaned_raw = json_match.group(1).strip()
        elif not cleaned_raw.startswith("{") and "{" in cleaned_raw:
            start = cleaned_raw.find("{")
            end = cleaned_raw.rfind("}")
            if start != -1 and end != -1:
                cleaned_raw = cleaned_raw[start:end+1]

        if not cleaned_raw:
            logger.warning("Uncone approval agent received empty response from Ollama — denying by default.")
            return ConeApprovalResult(approved=False, reason="Empty response from approval agent.")

        data = json.loads(cleaned_raw)
        result = ConeApprovalResult(
            approved=bool(data.get("approved", False)),
            reason=str(data.get("reason", "")),
        )
        logger.info(
            "Uncone approval [target: %s, requester: %s]: approved=%s — %s",
            cone_target, requester_username, result.approved, result.reason,
        )
        return result

    except json.JSONDecodeError as exc:
        logger.warning("Uncone approval agent JSON parse failed. Raw output: %r. Error: %s", raw, exc)
        return ConeApprovalResult(approved=False, reason="JSON parse failed.")
    except LLMError as exc:
        logger.warning("Uncone approval agent failed (%s) — denying by default.", exc)
        return ConeApprovalResult(
            approved=False,
            reason=f"Approval agent error: {exc}",
        )

