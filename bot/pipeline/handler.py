"""
process_message() — the single orchestration point for all incoming messages.

The platform layers (discord_bot, twitch_bot) call this function and get back
a response string. They never touch routing, context building, or LLM calls.

Responsibilities:
- Build the system prompt via ContextBuilder.
- Slice message history to the configured limit.
- Call the appropriate LLM client (text or vision).
- Return a clean, platform-length-capped response string.

Out of scope (Phase 3+):
- Intent routing via Gemma 4.
- RAG context injection.
- Tool calling by the LLM.
"""

from __future__ import annotations

import logging
import random
import re
from typing import Optional

from ..utils.config import get_config
from ..utils.exceptions import LLMRateLimitError, LLMError
from ..utils.llm import get_llm_client
from ..utils.llm.gemini import GeminiClient
from ..utils.models import Platform, UserState
from ..memory.state import StateManager
from .context import ContextBuilder

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
    "Ugh, whatever. I'm not in the mood right now.",
    "Can't be bothered right now.",
    "I'm not in the mood right now.",
    "Bother me later.",
    "Can't it wait? I'm busy.",
]


async def process_message(
    platform: Platform,
    user_state: UserState,
    message: str,
    state_manager: StateManager,
    context_builder: ContextBuilder,
    image_urls: Optional[list[str]] = None,
) -> str:
    """
    Orchestrate a complete message → response cycle.

    Args:
        platform:         Which platform the message came from.
        user_state:       Full state for the sending user.
        message:          Raw message content.
        state_manager:    Shared state manager (for mentioned-user lookups).
        context_builder:  Pre-built ContextBuilder instance.
        image_urls:       Optional list of image attachment URLs (Discord only).

    Returns:
        A response string, already capped to the platform's max message length.
    """
    cfg = get_config()

    # ------------------------------------------------------------------
    # 1. Build mentioned-user context
    # ------------------------------------------------------------------
    mentioned_names = context_builder.extract_mentioned_usernames(message)
    mentioned_states: list[tuple[str, UserState]] = []
    for name in mentioned_names:
        username_lower = name.lower()
        # Skip if it's the sender themselves
        if username_lower == user_state.primary_identity.username.lower():
            continue
        # Look up via state manager's username search
        discord_id = state_manager.find_discord_id_by_username(name)
        if discord_id:
            platform_key = f"discord_{discord_id}"
            mention_state = state_manager._users.get(platform_key)
            if mention_state:
                mentioned_states.append((name, mention_state))

    # ------------------------------------------------------------------
    # 2. Build system prompt
    # ------------------------------------------------------------------
    system_prompt = context_builder.build_system_prompt(
        user_state=user_state,
        platform=platform,
        current_message=message,
        mentioned_user_states=mentioned_states if mentioned_states else None,
    )

    # ------------------------------------------------------------------
    # 3. Build conversation history (sliced to history limit)
    # ------------------------------------------------------------------
    history_limit = cfg.memory.message_history_limit
    recent = user_state.recent_messages[-history_limit:]

    messages: list[dict] = []
    for msg in recent:
        role = "model" if msg.from_bot else "user"
        # Strip leftover markdown / chain-of-thought from bot messages
        content = _clean_bot_message(msg.content) if msg.from_bot else msg.content
        if content:
            messages.append({"role": role, "content": content})

    # Append the current message
    messages.append({"role": "user", "content": message})

    # ------------------------------------------------------------------
    # 4. Call the LLM
    # ------------------------------------------------------------------
    try:
        if image_urls:
            vision_client = get_llm_client("vision")
            if not isinstance(vision_client, GeminiClient):
                logger.error("Vision client is not a GeminiClient — cannot process images.")
                return random.choice(_ERROR_RESPONSES)
            response_text = await vision_client.generate_with_images(
                messages=messages,
                image_urls=image_urls,
                system_prompt=system_prompt,
            )
        else:
            chat_client = get_llm_client("chat")
            response_text = await chat_client.generate(
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
    # 5. Clean and cap the response
    # ------------------------------------------------------------------
    response_text = _clean_response(response_text)
    if not response_text:
        return random.choice(_ERROR_RESPONSES)

    max_len = (
        cfg.discord.max_message_length
        if platform == Platform.DISCORD
        else cfg.twitch.max_message_length
    )
    if len(response_text) > max_len:
        response_text = response_text[: max_len - 3] + "..."

    return response_text


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
