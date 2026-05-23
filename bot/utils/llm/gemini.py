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
from typing import Any, Optional

from google import genai
from google.genai import types

from .base import LLMClient
from ..exceptions import LLMError, LLMRateLimitError
from ..models import ConeOutcome, ConeToolCall

logger = logging.getLogger(__name__)


@dataclass
class ConeCallContext:
    """
    Bundles a parsed ConeToolCall with the raw Gemini Content from the
    generate_with_tools() call.

    The raw_model_content (types.Content) is needed to reconstruct the
    multi-turn conversation for send_tool_result() — Gemini requires the
    original function_call part to appear before the function_response.
    """
    call: ConeToolCall
    raw_model_content: Any  # types.Content containing the function_call Part


class GeminiClient(LLMClient):
    """
    Async Gemini client configured for a single role (chat, vision, or summary).

    Instantiated via get_llm_client(role) — do not construct directly in feature modules.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.9,
        top_p: float = 0.9,
        max_output_tokens: int = 1000,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self._gen_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_output_tokens,
        )

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
        try:
            contents = self._build_contents(messages)
            config = types.GenerateContentConfig(
                temperature=self._gen_config.temperature,
                top_p=self._gen_config.top_p,
                max_output_tokens=self._gen_config.max_output_tokens,
                system_instruction=system_prompt if system_prompt else None,
            )
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return self._extract_text(response)
        except Exception as exc:
            self._handle_exception(exc)

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
        try:
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

            config = types.GenerateContentConfig(
                temperature=self._gen_config.temperature,
                top_p=self._gen_config.top_p,
                max_output_tokens=self._gen_config.max_output_tokens,
                system_instruction=system_prompt if system_prompt else None,
                tools=[initiate_cone_tool],
            )

            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

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
                return cone_ctx, ""

            # Plain text response
            return None, self._extract_text(response)

        except Exception as exc:
            self._handle_exception(exc)

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
        try:
            contents = self._build_contents(messages)

            # Append Ghost's turn containing the function_call Part
            contents.append(raw_model_content)

            # Append the function_response as a user turn
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name="initiate_cone",
                            response=outcome.model_dump(exclude_none=True),
                        )
                    ],
                )
            )

            config = types.GenerateContentConfig(
                temperature=self._gen_config.temperature,
                top_p=self._gen_config.top_p,
                max_output_tokens=self._gen_config.max_output_tokens,
                system_instruction=system_prompt if system_prompt else None,
            )
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return self._extract_text(response)
        except Exception as exc:
            self._handle_exception(exc)

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
        try:
            contents = self._build_contents(messages)
            config = types.GenerateContentConfig(
                temperature=self._gen_config.temperature,
                top_p=self._gen_config.top_p,
                max_output_tokens=self._gen_config.max_output_tokens,
                system_instruction=system_prompt if system_prompt else None,
                response_mime_type="application/json",
            )
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return self._extract_text(response)
        except Exception as exc:
            self._handle_exception(exc)

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
        try:
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

            config = types.GenerateContentConfig(
                temperature=self._gen_config.temperature,
                top_p=self._gen_config.top_p,
                max_output_tokens=self._gen_config.max_output_tokens,
                system_instruction=system_prompt if system_prompt else None,
            )
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return self._extract_text(response)
        except Exception as exc:
            self._handle_exception(exc)

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
                            cone_target=str(args.get("cone_target", "")),
                            cone_effect=str(args.get("cone_effect", "uwu")),
                            cone_trigger=str(args.get("cone_trigger", "autonomous")),
                            cone_duration=args.get("cone_duration") or None,
                            cone_condition=args.get("cone_condition") or None,
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
