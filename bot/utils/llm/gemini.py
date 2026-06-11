"""
Gemini LLM client.

Wraps google-genai's async API. Handles chat, vision, and summary generation.
Cone tool declarations live here; the pipeline intercepts the function_call
and feeds a function_response back via send_tool_result() to get Ghost's
reactive reply based on what actually happened.
"""

from __future__ import annotations

import aiohttp
import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types

from .base import LLMClient
from ..exceptions import LLMError, LLMRateLimitError
from ..models import ConeOutcome, ConeToolCall

logger = logging.getLogger(__name__)


def get_la_today() -> str:
    """Get today's date formatted as YYYY-MM-DD in America/Los_Angeles timezone."""
    tz = ZoneInfo("America/Los_Angeles")
    now_la = datetime.now(tz)
    return now_la.strftime("%Y-%m-%d")


def get_next_pacific_midnight() -> datetime:
    """Get the next Pacific Midnight time converted to an offset-aware UTC datetime."""
    tz = ZoneInfo("America/Los_Angeles")
    now_la = datetime.now(tz)
    tomorrow_la = now_la.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return tomorrow_la.astimezone(timezone.utc)


class GeminiUsageTracker:
    """
    Crash-safe daily Gemini usage tracker and exhaustion state store using
    a generic MongoDB collection 'system_status'.
    """

    def __init__(self) -> None:
        # Import get_db dynamically to avoid circular import issues
        from bot.memory.db import get_db
        self._get_db = get_db

    def _get_coll(self) -> Any:
        return self._get_db().system_status

    async def get_daily_usage(self) -> tuple[int, int]:
        """
        Returns (chat_paid_calls, total_paid_calls) for today (America/Los_Angeles date).
        """
        try:
            coll = self._get_coll()
            today_str = get_la_today()
            doc = await coll.find_one({"_id": f"gemini_usage_{today_str}"})
            if not doc:
                return 0, 0
            return doc.get("chat_paid_calls", 0), doc.get("total_paid_calls", 0)
        except Exception as exc:
            logger.error("Failed to get daily gemini usage from mongo: %s", exc)
            return 0, 0

    async def increment_paid_calls(self, is_chat: bool) -> None:
        """
        Increment the paid chat and/or total calls for today.
        """
        try:
            coll = self._get_coll()
            today_str = get_la_today()
            inc_data: dict[str, int] = {"total_paid_calls": 1}
            if is_chat:
                inc_data["chat_paid_calls"] = 1
            
            # Upsert the daily document
            await coll.update_one(
                {"_id": f"gemini_usage_{today_str}"},
                {"$inc": inc_data},
                upsert=True
            )
        except Exception as exc:
            logger.error("Failed to increment paid calls in mongo: %s", exc)

    async def get_free_exhausted_until(self) -> Optional[datetime]:
        """
        Returns the UTC datetime until which the free API is considered exhausted.
        """
        try:
            coll = self._get_coll()
            doc = await coll.find_one({"_id": "gemini_status_global"})
            if not doc:
                return None
            val = doc.get("free_exhausted_until")
            if val:
                # Ensure it's offset-aware UTC datetime
                if val.tzinfo is None:
                    val = val.replace(tzinfo=timezone.utc)
                return val
            return None
        except Exception as exc:
            logger.error("Failed to get free exhausted until from mongo: %s", exc)
            return None

    async def set_free_exhausted_until(self, until: Optional[datetime]) -> None:
        """
        Sets the global free-tier daily exhaustion timestamp.
        """
        try:
            coll = self._get_coll()
            await coll.update_one(
                {"_id": "gemini_status_global"},
                {"$set": {"free_exhausted_until": until}},
                upsert=True
            )
        except Exception as exc:
            logger.error("Failed to set free exhausted until in mongo: %s", exc)


@dataclass
class ConeCallContext:
    """
    Bundles a parsed ConeToolCall with the raw Gemini Content from the
    generate_with_tools() call.

    The raw_model_content (types.Content) is needed to reconstruct the
    multi-turn conversation for send_tool_result() — Gemini requires the
    original function_call part to appear before the function_call.
    """
    call: ConeToolCall
    raw_model_content: Any  # types.Content containing the function_call Part


class GeminiClient(LLMClient):
    """
    Async Gemini client configured for a single role (chat, vision, or summary)
    with multi-key dynamic routing, budget caps, and daily Pacific Midnight resets.

    Instantiated via get_llm_client(role) — do not construct directly in feature modules.
    """

    def __init__(
        self,
        api_key_free: str,
        api_key_paid: Optional[str],
        preferred_source: str,
        role: str,
        model: str,
        temperature: float = 0.9,
        top_p: float = 0.9,
        max_output_tokens: int = 1000,
        thinking_budget: Optional[int] = None,
        enable_web_grounding: bool = False,
    ) -> None:
        self.api_key_free = api_key_free
        self.api_key_paid = api_key_paid
        self.preferred_source = preferred_source
        self.role = role
        self.model = model
        self.thinking_budget = thinking_budget
        self.enable_web_grounding = enable_web_grounding
        self._gen_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
        )
        self._client_free = genai.Client(api_key=api_key_free)
        self._client_paid = genai.Client(api_key=api_key_paid) if api_key_paid else None
        self._tracker = GeminiUsageTracker()

    def _build_generation_config(
        self,
        system_prompt: Optional[str] = None,
        response_mime_type: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> types.GenerateContentConfig:
        """Centralized helper to build GenerateContentConfig, dynamically injecting thinking budget."""
        config_args = {
            "temperature": self._gen_config.temperature,
            "top_p": self._gen_config.top_p,
            "max_output_tokens": self._gen_config.max_output_tokens,
            "system_instruction": system_prompt if system_prompt else None,
        }
        if response_mime_type:
            config_args["response_mime_type"] = response_mime_type

        # Build tools list, adding Google Search grounding if enabled
        resolved_tools = list(tools) if tools else []
        if self.enable_web_grounding:
            resolved_tools.append(types.Tool(google_search=types.GoogleSearch()))

        if resolved_tools:
            config_args["tools"] = resolved_tools

        if self.thinking_budget is not None and self.thinking_budget > 0:
            config_args["thinking_config"] = types.ThinkingConfig(thinking_budget=self.thinking_budget)

        return types.GenerateContentConfig(**config_args)

    @property
    def _is_chat(self) -> bool:
        return self.role in ("chat", "vision")

    async def _get_extra_info(self) -> str:
        """Helper to collect and format API budget and fallback state for logging."""
        try:
            chat_paid, total_paid = await self._tracker.get_daily_usage()
            exhausted_until = await self._tracker.get_free_exhausted_until()
            
            # Determine which key tier is active
            from datetime import datetime, timezone
            is_paid = self.preferred_source == "paid" or (
                exhausted_until is not None and datetime.now(timezone.utc) < exhausted_until
            )
            source = "Paid API" if is_paid else "Free API"
            
            limits_info = f"Paid calls: chat={chat_paid}, total={total_paid}"
            if exhausted_until:
                limits_info += f" | Free exhausted until {exhausted_until}"
            return f"Role: {self.role} | Source: {source} | {limits_info}"
        except Exception:
            return f"Role: {self.role} | Usage tracker metrics unavailable"

    async def _check_limits_and_select_client(self, force_paid: bool = False) -> tuple[genai.Client, bool]:
        """
        Determines whether to use the free or paid client.
        Enforces daily budget limits if using the paid client.

        Returns:
            (client, is_paid)
        """
        from bot.utils import get_config
        cfg = get_config()
        paid_limits = cfg.gemini.paid_limits

        use_paid = False

        # 1. Determine if we want/need to use paid client
        if self.preferred_source == "paid" or force_paid:
            use_paid = True
        else:
            # Check if free client is currently marked as exhausted
            exhausted_until = await self._tracker.get_free_exhausted_until()
            if exhausted_until:
                now_utc = datetime.now(timezone.utc)
                if now_utc < exhausted_until:
                    logger.info("Free Gemini API is marked exhausted until %s (UTC). Falling back to Paid API.", exhausted_until)
                    use_paid = True
                else:
                    # Time has passed, reset exhaustion status
                    logger.info("Free Gemini API exhaustion window has expired. Resetting status.")
                    await self._tracker.set_free_exhausted_until(None)

        # 2. If free client is selected, return it
        if not use_paid:
            return self._client_free, False

        # 3. If paid client is selected, verify it exists and enforce limits
        if not self._client_paid:
            # No paid key configured. Try falling back to free if we are not forcing paid
            if not force_paid:
                logger.warning("Paid Gemini API is selected/fallback active, but GEMINI_API_KEY_PAID is not set. Using free client.")
                return self._client_free, False
            raise LLMError("GEMINI_API_KEY_PAID environment variable is not set, but paid client is required.")

        # Enforce budget limits
        chat_paid, total_paid = await self._tracker.get_daily_usage()

        # Total limit across all roles
        if total_paid >= paid_limits.max_total_calls_per_day:
            raise LLMError(f"Daily paid Gemini budget cap reached: {total_paid}/{paid_limits.max_total_calls_per_day} calls.")

        # Chat limit on fallback usage
        if self._is_chat and chat_paid >= paid_limits.max_chat_calls_per_day:
            raise LLMError(f"Daily paid Gemini chat budget cap reached: {chat_paid}/{paid_limits.max_chat_calls_per_day} calls.")

        return self._client_paid, True

    async def _execute_with_retry(self, api_func: Any) -> Any:
        """
        Executes a Gemini API call using the correct client, handling in-flight daily fallback
        retries if the free client is rate limited.
        """
        client, is_paid = await self._check_limits_and_select_client()

        try:
            res = await api_func(client)
            if is_paid:
                await self._tracker.increment_paid_calls(is_chat=self._is_chat)
            return res
        except Exception as exc:
            # Self-healing: if the model does not support thinking_config, disable and retry instantly!
            if "thinking" in str(exc).lower() and self.thinking_budget is not None:
                logger.warning("Thinking config not supported for model %s — disabling and retrying.", self.model)
                self.thinking_budget = None
                return await self._execute_with_retry(api_func)
            try:
                self._handle_exception(exc)
            except LLMRateLimitError as rate_exc:
                if not is_paid:
                    logger.warning("Free Gemini API rate limited / exhausted. Flagging exhaustion and retrying on paid client.")

                    # Flag exhaustion in MongoDB until next Pacific Midnight
                    next_midnight = get_next_pacific_midnight()
                    await self._tracker.set_free_exhausted_until(next_midnight)

                    try:
                        paid_client, is_paid_now = await self._check_limits_and_select_client(force_paid=True)
                    except Exception as limit_exc:
                        logger.error("Failed to select paid client for fallback retry: %s", limit_exc)
                        raise rate_exc

                    try:
                        res = await api_func(paid_client)
                        await self._tracker.increment_paid_calls(is_chat=self._is_chat)
                        return res
                    except Exception as paid_exc:
                        logger.error("Fallback retry on paid Gemini API failed: %s", paid_exc)
                        self._handle_exception(paid_exc)
                else:
                    raise rate_exc
            except Exception as other_exc:
                raise other_exc

    # ------------------------------------------------------------------
    # Core generate — text only
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        """
        Generate a text response from conversation history.

        Args:
            messages:     [{"role": "user"|"model", "content": str}, …]
            system_prompt: Passed as Gemini system_instruction.

        Returns:
            Response text.

        Raises:
            LLMRateLimitError: on 429 / RESOURCE_EXHAUSTED.
            LLMError:          on any other API failure.
        """
        contents = self._build_contents(messages)
        async def _call(cli: genai.Client):
            config = self._build_generation_config(system_prompt=system_prompt)
            return await cli.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        response = await self._execute_with_retry(_call)
        res_text = self._extract_text(response)

        try:
            from bot.utils.logging import log_llm_call
            extra = await self._get_extra_info()
            log_llm_call("GeminiClient", self.model, system_prompt, messages, res_text, extra)
        except Exception as exc:
            logger.warning("Failed to log Gemini generate call: %s", exc)

        return res_text

    # ------------------------------------------------------------------
    # Tool-calling generate — with initiate_cone tool available
    # ------------------------------------------------------------------

    async def generate_with_tools(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> tuple[Optional[ConeCallContext], str]:
        """
        Generate a response with the initiate_cone tool available.

        Gemini generates plain text for the vast majority of messages.
        If it decides to cone someone, it outputs a function_call instead.
        The caller must follow up with send_tool_result() after running the
        cone pipeline, so Ghost can react to the actual outcome.

        Args:
            messages:      Conversation history.
            system_prompt: System context (includes Ghost's persona + any RAG chunks).

        Returns:
            (ConeCallContext, "")      if Gemini called initiate_cone.
            (None, "response text")   if Gemini generated a plain text reply.

        Raises:
            LLMRateLimitError: on 429 / RESOURCE_EXHAUSTED.
            LLMError:          on any other API failure.
        """
        contents = self._build_contents(messages)

        # Define the initiate_cone tool schema
        initiate_cone_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="initiate_cone",
                    description=(
                        "Apply a text transformation (cone) to a Discord user's messages. "
                        "Use this tool SPARINGLY — only when someone explicitly asks, "
                        "or when the conversation genuinely calls for it as a character moment. "
                        "Ghost will respond after learning whether the cone was applied or denied. "
                        "IMPORTANT: Prefer temporary cones — always set a duration or condition "
                        "unless the person explicitly asks for a permanent cone. "
                        "Use your judgement: a silly request warrants a few minutes or an hour, "
                        "a bigger offence might earn an hour or few hours. Permanent should be rare."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        required=[
                            "cone_target",
                            "cone_effect",
                            "cone_trigger",
                        ],
                        properties={
                            "cone_target": types.Schema(
                                type=types.Type.STRING,
                                description="Canonical Discord username of the person to cone.",
                            ),
                            "cone_effect": types.Schema(
                                type=types.Type.STRING,
                                description=(
                                    "Cone effect to apply. Must be one of: "
                                    "uwu, pirate, shakespeare, caveman, drunk, slayspeak, "
                                    "brainrot, scrum, linkedin, crisis, canadian, vsauce, "
                                    "bri, oni, dyslexia, bardify, valley, genz, corporate, "
                                    "emoji, existential, polite, conspiracy, british, "
                                    "censor, dickslexia, unga, drunkard."
                                ),
                            ),
                            "cone_trigger": types.Schema(
                                type=types.Type.STRING,
                                description=(
                                    "Why the cone is happening. Must be one of: "
                                    "'requested_approved' (an authorized user asked), "
                                    "'requested_unapproved' (a regular user asked), "
                                    "'autonomous' (your own spontaneous decision)."
                                ),
                            ),
                            "cone_duration": types.Schema(
                                type=types.Type.STRING,
                                description=(
                                    "How long the cone lasts. Use your own judgement — "
                                    "prefer a temporary duration (e.g. '5 minutes', '30 minutes', '2 hours', '6 hours', etc) "
                                    "unless the person explicitly asked to make it permanent. "
                                    "A minor silly request = a few minutes. "
                                    "A bigger offence or persistent annoyance = up to a few hours. "
                                    "Only omit this (making it permanent) if someone explicitly asked for that."
                                ),
                            ),
                            "cone_condition": types.Schema(
                                type=types.Type.STRING,
                                description=(
                                    "Condition for early removal (can be used instead of or alongside duration). "
                                    "e.g. 'until they say sorry', 'until they admit Ghost is always right'. "
                                    "Good for playful in-character moments — use this when it fits the vibe."
                                ),
                            ),
                        },
                    ),
                )
            ]
        )

        remove_cone_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="remove_cone",
                    description=(
                        "Remove an active text transformation (cone) from a Discord user's messages. "
                        "Use this tool when a user has been coned and has successfully convinced you to uncone them, "
                        "apologized, satisfied your removal condition, or if you decide to show mercy. "
                        "Ghost will respond after learning whether the cone was successfully removed."
                    ),
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        required=["cone_target"],
                        properties={
                            "cone_target": types.Schema(
                                type=types.Type.STRING,
                                description="Canonical Discord username of the person to uncone.",
                            ),
                        },
                    ),
                )
            ]
        )

        async def _call(cli: genai.Client):
            config = self._build_generation_config(
                system_prompt=system_prompt,
                tools=[initiate_cone_tool, remove_cone_tool],
            )
            return await cli.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

        response = await self._execute_with_retry(_call)

        # Log response structure for diagnostics
        try:
            finish_reason = response.candidates[0].finish_reason if response.candidates else "NO_CANDIDATES"
            num_parts = len(response.candidates[0].content.parts) if response.candidates else 0
            part_types = [
                "function_call" if hasattr(p, "function_call") and p.function_call else "text"
                for p in (response.candidates[0].content.parts if response.candidates else [])
            ]
            logger.debug(
                "[generate_with_tools] finish_reason=%s parts=%d types=%s",
                finish_reason, num_parts, part_types,
            )
        except Exception as diag_exc:
            logger.debug("[generate_with_tools] Could not read response structure: %s", diag_exc)

        # Check if the model called the tool
        cone_ctx = self._extract_cone_call_context(response)
        if cone_ctx is not None:
            try:
                from bot.utils.logging import log_llm_call
                extra = await self._get_extra_info()
                tool_log = f"[Tool Call] {cone_ctx.call.tool_name}(target='{cone_ctx.call.cone_target}', effect='{cone_ctx.call.cone_effect}', trigger='{cone_ctx.call.cone_trigger}', duration={cone_ctx.call.cone_duration}, condition={cone_ctx.call.cone_condition})"
                log_llm_call("GeminiClient", self.model, system_prompt, messages, tool_log, extra)
            except Exception as exc:
                logger.warning("Failed to log Gemini tool call: %s", exc)
            return cone_ctx, ""

        # Plain text response
        res_text = self._extract_text(response)
        try:
            from bot.utils.logging import log_llm_call
            extra = await self._get_extra_info()
            log_llm_call("GeminiClient", self.model, system_prompt, messages, res_text, extra)
        except Exception as exc:
            logger.warning("Failed to log Gemini plain text generate_with_tools call: %s", exc)
        return None, res_text

    # ------------------------------------------------------------------
    # Tool result follow-up — feed outcome back to Ghost
    # ------------------------------------------------------------------

    async def send_tool_result(
        self,
        messages: list[dict],
        system_prompt: str,
        raw_model_content: Any,
        outcome: ConeOutcome,
    ) -> str:
        """
        Send the cone pipeline outcome back to Gemini as a function_response
        and return Ghost's fresh, reactive reply.

        Gemini sees its own function_call turn, followed by the function_response
        describing what actually happened (applied, denied, error, etc.), and
        generates a contextually appropriate response in Ghost's voice.

        Args:
            messages:           The same conversation history passed to generate_with_tools.
            system_prompt:      The same system prompt (persona + RAG + anti-repetition).
            raw_model_content:  The types.Content from generate_with_tools containing
                                the original function_call Part.
            outcome:            Typed result of the full cone pipeline.

        Returns:
            Ghost's text response.

        Raises:
            LLMRateLimitError: on 429 / RESOURCE_EXHAUSTED.
            LLMError:          on any other API failure.
        """
        contents = self._build_contents(messages)

        # Append Ghost's turn containing the function_call Part
        contents.append(raw_model_content)

        # Resolve function name from raw_model_content
        func_name = "initiate_cone"
        if raw_model_content and hasattr(raw_model_content, "parts") and raw_model_content.parts:
            for part in raw_model_content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    func_name = part.function_call.name
                    break

        # Append the function_response as a user turn
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name=func_name,
                        response=outcome.model_dump(exclude_none=True),
                    )
                ],
            )
        )

        async def _call(cli: genai.Client):
            config = self._build_generation_config(system_prompt=system_prompt)
            return await cli.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

        response = await self._execute_with_retry(_call)
        res_text = self._extract_text(response)

        try:
            from bot.utils.logging import log_llm_call
            extra = await self._get_extra_info()

            # Reconstruct detailed messages showing the tool round-trip
            full_msgs = list(messages)
            full_msgs.append({"role": "model", "content": f"[Tool Call] {func_name}(...)"})
            full_msgs.append({"role": "user", "content": f"[Tool Response] {outcome.model_dump(exclude_none=True)}"})

            log_llm_call(
                "GeminiClient",
                self.model,
                system_prompt,
                full_msgs,
                res_text,
                f"{extra} (Tool Result Follow-up)",
            )
        except Exception as exc:
            logger.warning("Failed to log Gemini send_tool_result call: %s", exc)

        return res_text

    # ------------------------------------------------------------------
    # JSON generate — structured output mode
    # ------------------------------------------------------------------

    async def generate_json(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        """
        Generate a response with response_mime_type="application/json".

        Use this for extraction calls where the output must be valid JSON.
        The caller is responsible for parsing and validating the returned string.

        Args:
            messages:      Conversation history (same format as generate()).
            system_prompt: System context — should specify the expected JSON schema.

        Returns:
            Raw JSON string from the model.

        Raises:
            LLMRateLimitError: on 429 / RESOURCE_EXHAUSTED.
            LLMError:          on any other API failure or empty response.
        """
        contents = self._build_contents(messages)
        async def _call(cli: genai.Client):
            config = self._build_generation_config(
                system_prompt=system_prompt,
                response_mime_type="application/json",
            )
            return await cli.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        response = await self._execute_with_retry(_call)
        res_text = self._extract_text(response)

        try:
            from bot.utils.logging import log_llm_call
            extra = await self._get_extra_info()
            log_llm_call("GeminiClient", self.model, system_prompt, messages, res_text, f"{extra} (JSON)")
        except Exception as exc:
            logger.warning("Failed to log Gemini generate_json call: %s", exc)

        return res_text

    # ------------------------------------------------------------------
    # Vision generate — text + images
    # ------------------------------------------------------------------

    async def generate_with_images(
        self,
        messages: list[dict],
        image_urls: list[str],
        system_prompt: str = "",
    ) -> str:
        """
        Generate a response that includes analysis of one or more images.

        Images are downloaded from Discord CDN URLs and converted to inline bytes
        because Gemini cannot fetch external URLs directly.

        Args:
            messages:     Conversation history (text only; images appended separately).
            image_urls:   HTTP(S) URLs pointing to images (Discord attachments, etc.).
            system_prompt: System context for the model.

        Returns:
            Response text.
        """
        contents = self._build_contents(messages)

        # Fetch and attach each image as inline bytes
        image_parts: list[types.Part] = []
        for url in image_urls:
            image_bytes, mime_type = await self._download_image(url)
            if image_bytes:
                image_parts.append(
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                )
            else:
                logger.warning("Failed to download image from %s — skipping", url)

        if image_parts:
            # Append a new user turn that contains all images
            contents.append(
                types.Content(role="user", parts=image_parts)
            )

        async def _call(cli: genai.Client):
            config = self._build_generation_config(system_prompt=system_prompt)
            return await cli.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

        response = await self._execute_with_retry(_call)
        res_text = self._extract_text(response)

        try:
            from bot.utils.logging import log_llm_call
            extra = await self._get_extra_info()
            
            # Reconstruct history messages to include [Image attached: URL]
            logged_messages = list(messages)
            for url in image_urls:
                logged_messages.append({"role": "user", "content": f"[Image attached: {url}]"})
                
            log_llm_call("GeminiClient", self.model, system_prompt, logged_messages, res_text, f"{extra} (Vision)")
        except Exception as exc:
            logger.warning("Failed to log Gemini generate_with_images call: %s", exc)

        return res_text

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_contents(self, messages: list[dict]) -> list[types.Content]:
        """Convert OpenAI-style message dicts to Gemini Content objects."""
        contents: list[types.Content] = []
        for msg in messages:
            raw_role = msg.get("role", "user")
            # Gemini only accepts "user" or "model"
            role = "model" if raw_role == "assistant" else "user"
            text = msg.get("content", "")
            if text:
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=text)])
                )
        return contents

    def _extract_text(self, response) -> str:
        """Safely pull text from a Gemini GenerateContentResponse."""
        if hasattr(response, "text") and response.text:
            return response.text
        # Walk candidates → parts as a fallback
        try:
            parts = response.candidates[0].content.parts
            return "".join(p.text for p in parts if hasattr(p, "text") and p.text)
        except (AttributeError, IndexError):
            raise LLMError("Gemini returned an empty or unparseable response.")

    def _extract_cone_call_context(self, response) -> Optional[ConeCallContext]:
        """
        Check if the Gemini response contains an initiate_cone function call.

        Returns ConeCallContext (parsed call + raw Content for replay) if the
        tool was called, None for plain text responses.
        """
        try:
            candidate = response.candidates[0]
            raw_content = candidate.content  # preserve for send_tool_result replay
            parts = raw_content.parts
            for part in parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    logger.debug("[_extract_cone_call_context] Found function_call: name=%s", fc.name)
                    if fc.name == "initiate_cone":
                        args: dict[str, Any] = dict(fc.args)
                        call = ConeToolCall(
                            tool_name="initiate_cone",
                            cone_target=str(args.get("cone_target", "")),
                            cone_effect=str(args.get("cone_effect", "uwu")),
                            cone_trigger=str(args.get("cone_trigger", "autonomous")),
                            cone_duration=args.get("cone_duration") or None,
                            cone_condition=args.get("cone_condition") or None,
                        )
                        return ConeCallContext(call=call, raw_model_content=raw_content)
                    elif fc.name == "remove_cone":
                        args: dict[str, Any] = dict(fc.args)
                        call = ConeToolCall(
                            tool_name="remove_cone",
                            cone_target=str(args.get("cone_target", "")),
                            cone_effect="uwu",  # placeholder
                            cone_trigger="autonomous",  # placeholder
                        )
                        return ConeCallContext(call=call, raw_model_content=raw_content)
        except (AttributeError, IndexError, KeyError) as exc:
            logger.debug("[_extract_cone_call_context] Failed to extract tool call: %s", exc)
        return None

    async def _download_image(self, url: str) -> tuple[Optional[bytes], str]:
        """Download an image URL to raw bytes. Returns (bytes, mime_type) or (None, '')."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error("Image download failed for %s — HTTP %s", url, resp.status)
                        return None, ""
                    image_bytes = await resp.read()
                    content_type = resp.headers.get("content-type", "")
                    if "image" not in content_type:
                        # Guess from URL extension
                        url_lower = url.lower()
                        if url_lower.endswith(".png"):
                            content_type = "image/png"
                        elif url_lower.endswith(".gif"):
                            content_type = "image/gif"
                        elif url_lower.endswith(".webp"):
                            content_type = "image/webp"
                        else:
                            content_type = "image/jpeg"
                    return image_bytes, content_type
        except Exception as exc:
            logger.error("Exception downloading image %s: %s", url, exc)
            return None, ""

    def _handle_exception(self, exc: Exception) -> None:
        """Translate API exceptions into GhostError subclasses."""
        msg = str(exc).lower()
        if "429" in msg or "resource_exhausted" in msg or "rate" in msg:
            raise LLMRateLimitError(f"Gemini rate limit: {exc}") from exc
        raise LLMError(f"Gemini API error: {exc}") from exc
