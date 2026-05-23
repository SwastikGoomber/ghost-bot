"""
Gemini LLM client.

Wraps google-genai's async API. Handles chat, vision, and summary generation.
No tool declarations are registered here — cone operations are handled
entirely by the pipeline after the router phase (Phase 3).
"""

from __future__ import annotations

import aiohttp
import base64
import logging
from typing import Optional

from google import genai
from google.genai import types

from .base import LLMClient
from ..exceptions import LLMError, LLMRateLimitError

logger = logging.getLogger(__name__)


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
