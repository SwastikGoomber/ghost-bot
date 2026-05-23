"""
process_message() — the single orchestration point for all incoming messages.

Phase 6 changes:
  - Cone pipeline now uses a reactive two-call pattern:
      1. generate_with_tools() — Ghost decides to cone and returns a ConeCallContext.
      2. The approval pipeline runs, the cone is applied (or denied/errored).
      3. send_tool_result() — Ghost generates a fresh response based on the actual outcome.
  - Ghost never pre-writes responses; it reacts to what actually happened.
  - All cone failures (denied, target unknown, apply error, unexpected exception)
    produce a typed ConeOutcome that is fed back to Ghost for a natural reply.

Platform layers (discord_bot, twitch_bot) call this function and receive
a plain response string.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re

from typing import Optional

from ..utils.config import get_config
from ..utils.exceptions import LLMRateLimitError, LLMError, ConeEffectNotFoundError
from ..utils.llm import get_llm_client
from ..utils.llm.gemini import GeminiClient, ConeCallContext
from ..utils.models import (
    ChannelContextMessage,
    ConeOutcome,
    Platform,
    RetrievedChunk,
    TaxonomySnapshot,
    UserState,
)
from ..memory.state import StateManager
from ..memory.rag import retrieve, format_for_injection
from ..cone import apply_effect
from ..cone.effects.registry import resolve as resolve_effect
from .context import ContextBuilder
from .router import IntentRouter
from .rag_planner import RAGQueryPlanner
from bot.pipeline.cone_approval import run_cone_approval, record_cone_applied, run_uncone_approval

logger = logging.getLogger(__name__)

# Responses used when the LLM is unavailable (rate limit, quota, etc.)
_RATE_LIMIT_RESPONSES = [
    "Mom says I gotta sleep. Whatever.",
    "I'm done for today, peace.",
    "Gonna go blast some music and sleep",
    "That's enough social interaction for one day",
    "Calling it. See ya tomorrow I guess",
    "Done with today. Later.",
]

_ERROR_RESPONSES = [
    "I feel some disturbance in the air... is it a bird? is it a plane? no! it's goomber fucking shit up again. broke my comms. ttyl.",
    "Something broke on my end and I'm like 90 percent sure it's goomber. He does this. Constantly! BRB!",
    "My brain just stopped working for a sec. Goomber probably tripped over a server cable or something, give me a moment.",
    "Ah shit! I left the oven on! Talk later!",
    "Comms signal lost... try again in a bit.",
    "Hold on, be right back, just gotta get some milk.",
    "Can't reach my brain rn. Either goomber broke something or I'm having an existential moment, probably both",
]

# Module-level singleton router and taxonomy cache
_router = IntentRouter()
_taxonomy_snapshot: Optional[TaxonomySnapshot] = None
_taxonomy_lock = asyncio.Lock()


async def get_taxonomy(force_refresh: bool = False) -> TaxonomySnapshot:
    """
    Return the cached TaxonomySnapshot, building it on first call.

    Thread-safe via asyncio.Lock. Call with force_refresh=True after ingestion.
    """
    global _taxonomy_snapshot
    async with _taxonomy_lock:
        if _taxonomy_snapshot is None or force_refresh:
            try:
                from ..memory.rag.store import get_taxonomy_snapshot
                _taxonomy_snapshot = await get_taxonomy_snapshot()
                logger.info(
                    "Taxonomy snapshot loaded: %d individuals, %d arc tags, %d doc types.",
                    len(_taxonomy_snapshot.known_individuals),
                    len(_taxonomy_snapshot.arc_tags),
                    len(_taxonomy_snapshot.doc_type_counts),
                )
            except Exception as exc:
                logger.warning("Failed to build taxonomy snapshot (%s) — using empty.", exc)
                _taxonomy_snapshot = TaxonomySnapshot()
    return _taxonomy_snapshot


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def process_message(
    platform: Platform,
    user_state: UserState,
    message: str,
    state_manager: StateManager,
    context_builder: ContextBuilder,
    cone_manager=None,
    image_urls: Optional[list[str]] = None,
    channel_context: Optional[list[ChannelContextMessage]] = None,
    reply_context: Optional[ChannelContextMessage] = None,
) -> str:
    """
    Orchestrate a complete message → response cycle.

    Args:
        platform:         Which platform the message came from.
        user_state:       Full state for the sending user.
        message:          Raw message content.
        state_manager:    Shared state manager (for mentioned-user lookups).
        context_builder:  Pre-built ContextBuilder instance.
        cone_manager:     Active ConeManager instance (required for cone flow).
        image_urls:       Optional list of image attachment URLs (Discord only).
        channel_context:  Recent ambient messages from the current channel.
        reply_context:    Message being replied to, if any.

    Returns:
        A response string, already capped to the platform's max message length.
        The caller is responsible for saving this string to chat history.
    """
    cfg = get_config()

    # ------------------------------------------------------------------
    # 1. Run the intent router (fast local classification)
    # ------------------------------------------------------------------
    if platform == Platform.TWITCH and not cfg.twitch.enable_router:
        logger.debug("Bypassing IntentRouter classification for Twitch as configured.")
        flags = RouterFlags(rag_required=False, cone_relevant=False)
    else:
        flags = await _router.classify(
            message,
            recent_messages=list(user_state.recent_messages[-4:]),
        )
    logger.debug("RouterFlags: rag=%s, cone=%s", flags.rag_required, flags.cone_relevant)

    # ------------------------------------------------------------------
    # 2. Build mentioned-user context
    # ------------------------------------------------------------------
    sender_discord_id = (
        user_state.identifiers["discord"].user_id
        if "discord" in user_state.identifiers else ""
    )

    # Pass A: explicit @mentions + special_users.json variants
    mentioned_discord_ids: set[str] = set()
    for name_or_id in context_builder.extract_mentioned_usernames(message):
        discord_id = state_manager.find_discord_id_by_username(name_or_id)
        if discord_id and discord_id != sender_discord_id:
            mentioned_discord_ids.add(discord_id)

    # Pass B: free-text alias/name scan (exact + fuzzy at 0.80 cutoff)
    for discord_id in state_manager.scan_message_for_users(
        message, exclude_discord_id=sender_discord_id or None
    ):
        mentioned_discord_ids.add(discord_id)

    if reply_context and reply_context.user_id:
        discord_id = state_manager.find_discord_id_by_username(reply_context.user_id)
        if discord_id and discord_id != sender_discord_id:
            mentioned_discord_ids.add(discord_id)

    # Build (display_name, UserState) pairs, deduped by object identity
    mentioned_states: list[tuple[str, UserState]] = []
    seen_mention_obj_ids: set[int] = set()
    for discord_id in mentioned_discord_ids:
        mention_state = state_manager._users.get(f"discord_{discord_id}")
        if mention_state and id(mention_state) not in seen_mention_obj_ids:
            seen_mention_obj_ids.add(id(mention_state))
            discord_identity = mention_state.identifiers.get("discord")
            display = (
                discord_identity.display_name or discord_identity.username
                if discord_identity else mention_state.primary_name
            )
            mentioned_states.append((display, mention_state))

    # ------------------------------------------------------------------
    # 3. Parallel: RAG retrieval (if needed)
    # ------------------------------------------------------------------
    rag_chunks: list[RetrievedChunk] = []
    rag_allowed_for_platform = (
        platform == Platform.DISCORD
        or (platform == Platform.TWITCH and cfg.rag.enable_twitch_retrieval)
    )
    if flags.rag_required and cfg.rag.enabled and rag_allowed_for_platform:
        try:
            taxonomy = await get_taxonomy()
            planner = RAGQueryPlanner(taxonomy)
            query = await planner.plan(message)
            alias_map = state_manager.build_name_alias_map()
            rag_chunks = await retrieve(query, taxonomy=taxonomy, alias_map=alias_map)
            # Filter out low-quality chunks (significance < 2 if all are low)
            if rag_chunks and all(c.significance < 2 for c in rag_chunks):
                logger.debug("All RAG chunks have low significance — skipping injection.")
                rag_chunks = []
        except Exception as exc:
            logger.warning("RAG retrieval failed (%s) — continuing without context.", exc)
    elif flags.rag_required and cfg.rag.enabled:
        logger.debug("RAG retrieval skipped for platform=%s by config.", platform.value)

    # ------------------------------------------------------------------
    # 4. Build system prompt
    # ------------------------------------------------------------------
    rag_context = format_for_injection(rag_chunks) if rag_chunks else ""

    system_prompt = context_builder.build_system_prompt(
        user_state=user_state,
        platform=platform,
        current_message=message,
        mentioned_user_states=mentioned_states if mentioned_states else None,
        rag_context=rag_context or None,
        cone_requested=flags.cone_relevant,
        channel_context=channel_context,
        reply_context=reply_context,
    )

    # ------------------------------------------------------------------
    # 5. Build conversation history (sliced to history limit)
    # ------------------------------------------------------------------
    history_limit = cfg.memory.message_history_limit
    recent = user_state.recent_messages[-history_limit:]

    messages: list[dict] = []
    for msg in recent:
        role = "model" if msg.from_bot else "user"
        content = _clean_bot_message(msg.content) if msg.from_bot else msg.content
        if content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    # ------------------------------------------------------------------
    # 6. Call the LLM
    # ------------------------------------------------------------------
    try:
        if image_urls:
            # Vision path: no tool calling (images + tools can conflict on some models)
            vision_client = get_llm_client("vision")
            if not isinstance(vision_client, GeminiClient):
                logger.error("Vision client is not GeminiClient — cannot process images.")
                return random.choice(_ERROR_RESPONSES)
            response_text = await vision_client.generate_with_images(
                messages=messages,
                image_urls=image_urls,
                system_prompt=system_prompt,
            )
            cone_call = None
        else:
            chat_client = get_llm_client("chat")
            if not isinstance(chat_client, GeminiClient):
                # Fallback for unexpected client type
                response_text = await chat_client.generate(
                    messages=messages,
                    system_prompt=system_prompt,
                )
                cone_call = None
            else:
                # Primary path: tool-calling mode
                cone_call, response_text = await chat_client.generate_with_tools(
                    messages=messages,
                    system_prompt=system_prompt,
                )

    except LLMRateLimitError:
        logger.warning("LLM rate limit hit.")
        return random.choice(_RATE_LIMIT_RESPONSES)
    except LLMError as exc:
        logger.error("LLM error: %s", exc)
        return random.choice(_ERROR_RESPONSES)

    # ------------------------------------------------------------------
    # 7. Handle cone tool call (if Gemini used initiate_cone)
    # ------------------------------------------------------------------
    final_text: str
    if cone_call is not None and cone_manager is not None:
        final_text = await _handle_cone_call(
            cone_ctx=cone_call,
            requester_state=user_state,
            recent_messages=list(recent),
            cone_manager=cone_manager,
            state_manager=state_manager,
            chat_client=chat_client,
            messages=messages,
            system_prompt=system_prompt,
        )
    elif cone_call is not None and cone_manager is None:
        # Platform does not support cone operations (e.g. Twitch).
        # Feed a denial outcome back to Ghost so it can respond naturally.
        denial_outcome = ConeOutcome(
            status="denied",
            target=cone_call.call.cone_target,
            reason="Cone operations are not available on this platform.",
        )
        try:
            final_text = await chat_client.send_tool_result(
                messages=messages,
                system_prompt=system_prompt,
                raw_model_content=cone_call.raw_model_content,
                outcome=denial_outcome,
            )
        except Exception:
            final_text = random.choice(_ERROR_RESPONSES)
    else:
        final_text = response_text or ""

    # ------------------------------------------------------------------
    # 8. Clean and cap the response
    # ------------------------------------------------------------------
    final_text = _clean_response(final_text)
    if not final_text:
        return random.choice(_ERROR_RESPONSES)

    max_len = (
        cfg.discord.max_message_length
        if platform == Platform.DISCORD
        else cfg.twitch.max_message_length
    )
    if len(final_text) > max_len:
        final_text = final_text[: max_len - 3] + "..."

    return final_text


# ---------------------------------------------------------------------------
# Cone call handler
# ---------------------------------------------------------------------------

async def _handle_cone_call(
    cone_ctx: ConeCallContext,
    requester_state: UserState,
    recent_messages: list,
    cone_manager,
    state_manager: StateManager,
    chat_client: GeminiClient,
    messages: list[dict],
    system_prompt: str,
) -> str:
    """
    Run the full cone pipeline and return Ghost's reactive response.

    Flow:
        1. Validate effect + trigger.
        2. Run two-tier approval pipeline.
        3. Attempt apply (if approved).
        4. Build a typed ConeOutcome describing the actual result.
        5. Feed the outcome back via chat_client.send_tool_result().
        6. Return Ghost's fresh, contextual response.

    All failure modes (denied, target unknown, apply error, unexpected exception)
    produce a ConeOutcome so Ghost can react naturally to every scenario.
    Goomber blame strings are the last-resort fallback if send_tool_result fails.
    """
    cone_call = cone_ctx.call
    requester_username = requester_state.primary_identity.username or ""

    if cone_call.tool_name == "remove_cone":
        # 1. Run uncone approval
        approval = await run_uncone_approval(
            cone_target=cone_call.cone_target,
            requester_username=requester_username,
            recent_messages=recent_messages,
            requester_state=requester_state,
            cone_manager=cone_manager,
        )

        # 2. Build ConeOutcome based on result
        if not approval.approved:
            logger.debug(
                "Uncone denied for %s: %s",
                cone_call.cone_target, approval.reason,
            )
            outcome = ConeOutcome(
                status="denied",
                target=cone_call.cone_target,
                reason=approval.reason,
            )
        else:
            # Resolve target → Discord ID
            target_discord_id = cone_manager.find_discord_id_by_username(cone_call.cone_target)
            if not target_discord_id:
                logger.warning(
                    "Could not resolve uncone target '%s' to a Discord ID.",
                    cone_call.cone_target,
                )
                outcome = ConeOutcome(
                    status="target_unknown",
                    target=cone_call.cone_target,
                    reason=(
                        f"Could not find '{cone_call.cone_target}' in Discord. "
                        "Ask the user to @mention them or use their exact username."
                    ),
                )
            else:
                # Attempt remove
                try:
                    result = await cone_manager.remove(
                        discord_id=target_discord_id,
                        removed_by=requester_username,
                    )
                except Exception as exc:
                    logger.error(
                        "ConeManager.remove() raised unexpectedly for target '%s': %s",
                        cone_call.cone_target, exc, exc_info=True,
                    )
                    outcome = ConeOutcome(
                        status="error",
                        target=cone_call.cone_target,
                        reason="A technical error occurred while removing the cone.",
                    )
                else:
                    if result.success:
                        logger.info(
                            "Cone removed from: %s (%s)",
                            cone_call.cone_target, target_discord_id,
                        )
                        outcome = ConeOutcome(
                            status="unconed",
                            target=cone_call.cone_target,
                            reason=approval.reason,
                        )
                    else:
                        logger.warning("ConeManager.remove() returned failure: %s", result.message)
                        outcome = ConeOutcome(
                            status="uncone_failed",
                            target=cone_call.cone_target,
                            reason=result.message,
                        )
    else:
        # 1. Validate effect (default to uwu on unknown)
        try:
            canonical_effect = resolve_effect(cone_call.cone_effect)
        except Exception:
            logger.warning("Unknown cone effect '%s' — defaulting to 'uwu'.", cone_call.cone_effect)
            canonical_effect = "uwu"

        # 2. Validate trigger
        valid_triggers = {"requested_approved", "requested_unapproved", "autonomous"}
        cone_trigger = cone_call.cone_trigger if cone_call.cone_trigger in valid_triggers else "autonomous"

        # Pipeline safeguard: if requester is an authorized user, force/promote trigger to requested_approved
        cfg = get_config()
        if requester_username.lower() in cfg.cone.permissions:
            cone_trigger = "requested_approved"

        # 3. Run two-tier approval
        approval = await run_cone_approval(
            cone_target=cone_call.cone_target,
            cone_trigger=cone_trigger,
            cone_effect=canonical_effect,
            requester_username=requester_username,
            recent_messages=recent_messages,
            requester_state=requester_state,
            cone_manager=cone_manager,
        )

        # 4. Build ConeOutcome based on result
        if not approval.approved:
            logger.debug(
                "Cone denied for %s (%s): %s",
                cone_call.cone_target, cone_trigger, approval.reason,
            )
            outcome = ConeOutcome(
                status="denied",
                target=cone_call.cone_target,
                effect=canonical_effect,
                reason=approval.reason,
            )
        else:
            # Resolve target → Discord ID
            target_discord_id = cone_manager.find_discord_id_by_username(cone_call.cone_target)
            if not target_discord_id:
                logger.warning(
                    "Could not resolve cone target '%s' to a Discord ID.",
                    cone_call.cone_target,
                )
                outcome = ConeOutcome(
                    status="target_unknown",
                    target=cone_call.cone_target,
                    effect=canonical_effect,
                    reason=(
                        f"Could not find '{cone_call.cone_target}' in Discord. "
                        "Ask the user to @mention them or use their exact username."
                    ),
                )
            else:
                # Attempt apply — catch all exceptions
                try:
                    result = await cone_manager.apply(
                        discord_id=target_discord_id,
                        effect=canonical_effect,
                        applied_by=requester_username,
                        reason=cone_trigger,
                        duration=cone_call.cone_duration,
                        condition=cone_call.cone_condition,
                    )
                except Exception as exc:
                    logger.error(
                        "ConeManager.apply() raised unexpectedly for target '%s': %s",
                        cone_call.cone_target, exc, exc_info=True,
                    )
                    outcome = ConeOutcome(
                        status="error",
                        target=cone_call.cone_target,
                        effect=canonical_effect,
                        reason="A technical error occurred while applying the cone.",
                    )
                else:
                    if result.success:
                        record_cone_applied(cone_call.cone_target, cone_trigger)
                        logger.info(
                            "Cone applied: %s → %s (%s), trigger=%s",
                            canonical_effect, cone_call.cone_target, target_discord_id, cone_trigger,
                        )
                        outcome = ConeOutcome(
                            status="applied",
                            target=cone_call.cone_target,
                            effect=canonical_effect,
                            duration=cone_call.cone_duration,
                            condition=cone_call.cone_condition,
                            reason=approval.reason,
                        )
                    else:
                        logger.warning("ConeManager.apply() returned failure: %s", result.message)
                        outcome = ConeOutcome(
                            status="apply_failed",
                            target=cone_call.cone_target,
                            effect=canonical_effect,
                            reason=result.message,
                        )

    # 5. Feed outcome back to Ghost and get a fresh, reactive response
    try:
        if outcome.status == "applied":
            system_prompt += (
                "\n\nCRITICAL CONE ANNOUNCEMENT RULE:\n"
                "The cone has been successfully applied to the target! You MUST explicitly announce "
                "the cone details in character in your response. State exactly which effect was applied, "
                "how long it lasts (the duration, if temporary), or what condition is required to remove it early. "
                "This ensures everyone in chat knows what got applied, for how long, and how they can get free. "
                "Keep this announcement completely natural, sassy, and fully in character!"
            )
        elif outcome.status == "unconed":
            system_prompt += (
                "\n\nCRITICAL CONE REMOVAL ANNOUNCEMENT RULE:\n"
                "The cone has been successfully removed/lifted from the target! You MUST explicitly announce "
                "this to the user in character in your response. State that they are now free from the cone. "
                "Keep this announcement completely natural, sassy, and fully in character!"
            )

        response = await chat_client.send_tool_result(
            messages=messages,
            system_prompt=system_prompt,
            raw_model_content=cone_ctx.raw_model_content,
            outcome=outcome,
        )
        return response
    except LLMRateLimitError:
        logger.warning("Rate limit hit during cone tool_result follow-up.")
        return random.choice(_RATE_LIMIT_RESPONSES)
    except Exception as exc:
        logger.error("send_tool_result failed: %s", exc, exc_info=True)
        return random.choice(_ERROR_RESPONSES)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _clean_response(text: str) -> str:
    """
    Normalise a raw LLM response:
    - Remove <think>…</think> chain-of-thought blocks.
    - Strip leaked JSON tool-call blocks.
    - Remove meta-commentary lines (Raw response:, Ghost:, etc.).
    - Collapse multiple newlines into a single space.
    - Strip surrounding quotes.
    """
    # Remove chain-of-thought
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Remove JSON code blocks (should never appear — belt-and-suspenders)
    text = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)

    lines = text.split("\n")
    _skip_prefixes = (
        "incorporating the spirit",
        "also:",
        "raw response:",
        "cleaned response:",
        "user:",
        "assistant:",
        "ghost:",
    )
    cleaned = [
        line
        for line in lines
        if line.strip() and not line.strip().lower().startswith(_skip_prefixes)
    ]

    if not cleaned:
        return ""

    text = " ".join(cleaned)
    text = text.replace("USER:", "").replace("ASSISTANT:", "").strip()
    text = re.sub(r"\[Ghost\]:", "", text, flags=re.IGNORECASE)
    text = text.replace("Ghost:", "").strip()
    text = text.strip('"').strip("'")
    text = re.sub(r"\([^)]*\)", "", text)         # Remove (parenthetical notes)
    text = re.sub(r"([!?.:]){2,}", r"\1", text)   # Collapse repeated punctuation
    return text.strip()


def _clean_bot_message(text: str) -> str:
    """Light clean for injecting past bot messages into history (less aggressive)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)
    return text.strip()
