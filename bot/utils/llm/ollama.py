"""
Ollama LLM client.

Handles two distinct capabilities:
  - generate()  — text generation for the Gemma 4 intent router (Phase 3)
  - embed()     — vector embeddings via nomic-embed-text (Phase 4 RAG)

Uses the Ollama HTTP API directly via aiohttp. Ollama must be running locally
at OLLAMA_BASE_URL (default: http://localhost:11434).

Usage via registry (never instantiate directly in feature code):
    client = get_llm_client("router")   # for text generation
    client = get_llm_client("embed")    # for embeddings
"""

from __future__ import annotations

import logging

import aiohttp

from .base import LLMClient
from ..exceptions import LLMError

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """Client for local Ollama models."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        num_predict: int = 128,
        role: str = "",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.num_predict = num_predict
        self.role = role

    # ------------------------------------------------------------------
    # Text generation — /api/chat
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        """
        Generate a text response via Ollama's /api/chat endpoint.

        Args:
            messages:      [{"role": "user"|"assistant", "content": str}, …]
            system_prompt: Injected as a leading "system" message if provided.

        Returns:
            The model's response text.

        Raises:
            LLMError: if Ollama is unreachable or returns an error.
        """
        ollama_messages: list[dict] = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            # Normalise "model" → "assistant" for Ollama's OpenAI-compatible format
            if role == "model":
                role = "assistant"
            ollama_messages.append({"role": role, "content": msg.get("content", "")})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise LLMError(
                            f"Ollama /api/chat returned HTTP {resp.status}: {body}"
                        )
                    data = await resp.json()
                    content = data["message"]["content"]
                    logger.debug(
                        "[Ollama:chat] model=%s | prompt_tokens=%s | response: %r",
                        self.model,
                        data.get("prompt_eval_count", "?"),
                        content[:500],
                    )
                    try:
                        from bot.utils.logging import log_llm_call
                        log_llm_call(
                            client_name="OllamaClient",
                            model=self.model,
                            system_prompt=system_prompt,
                            messages=messages,
                            response=content,
                            extra_info=f"Role: {self.role}",
                        )
                    except Exception as exc:
                        logger.warning("Failed to log Ollama generate call: %s", exc)
                    return content
        except aiohttp.ClientConnectorError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Is Ollama running? (ollama serve)"
            ) from exc
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape from Ollama: {exc}") from exc

    # ------------------------------------------------------------------
    # JSON generation — /api/chat with format="json"
    # ------------------------------------------------------------------

    async def generate_json(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        """
        Generate a JSON-mode response from Ollama.

        Same as generate() but sets format="json" in the payload, which instructs
        Ollama to constrain the model's output to valid JSON.

        Args:
            messages:      Conversation history.
            system_prompt: System context — should describe the expected JSON schema.

        Returns:
            Raw JSON string.

        Raises:
            LLMError: if Ollama is unreachable or returns an error.
        """
        ollama_messages: list[dict] = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            if role == "model":
                role = "assistant"
            ollama_messages.append({"role": role, "content": msg.get("content", "")})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(
                    "[Ollama:json] model=%s num_predict=%d | sending %d messages",
                    self.model, self.num_predict, len(payload["messages"]),
                )
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise LLMError(
                            f"Ollama /api/chat (JSON mode) returned HTTP {resp.status}: {body}"
                        )
                    data = await resp.json()
                    content = data["message"]["content"]
                    logger.debug(
                        "[Ollama:json] model=%s | eval_count=%s | raw_response: %r",
                        self.model,
                        data.get("eval_count", "?"),
                        content[:500],
                    )
                    try:
                        from bot.utils.logging import log_llm_call
                        log_llm_call(
                            client_name="OllamaClient",
                            model=self.model,
                            system_prompt=system_prompt,
                            messages=messages,
                            response=content,
                            extra_info=f"Role: {self.role} (JSON)",
                        )
                    except Exception as exc:
                        logger.warning("Failed to log Ollama generate_json call: %s", exc)
                    return content
        except aiohttp.ClientConnectorError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Is Ollama running? (ollama serve)"
            ) from exc
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected Ollama JSON response shape: {exc}") from exc

    # ------------------------------------------------------------------
    # Embeddings — /api/embed
    # ------------------------------------------------------------------

    async def embed(self, text: str) -> list[float]:
        """
        Generate a vector embedding for the given text.

        Uses Ollama's /api/embed endpoint with the model configured for this client.
        For the RAG pipeline, this client is initialised with model="nomic-embed-text".
        Returns 768-dimensional vectors.

        Args:
            text: The text to embed (typically: summary + space-joined free_labels).

        Returns:
            A flat list of floats (768 dimensions for nomic-embed-text).

        Raises:
            LLMError: if Ollama is unreachable or returns an error.
        """
        payload = {
            "model": self.model,
            "input": text,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/embed",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise LLMError(
                            f"Ollama /api/embed returned HTTP {resp.status}: {body}"
                        )
                    data = await resp.json()
                    # Ollama returns {"embeddings": [[...vector...]]}
                    embeddings = data.get("embeddings")
                    if not embeddings or not embeddings[0]:
                        raise LLMError("Ollama /api/embed returned an empty embedding.")
                    return embeddings[0]
        except aiohttp.ClientConnectorError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Is Ollama running with nomic-embed-text pulled? "
                "(ollama serve && ollama pull nomic-embed-text)"
            ) from exc
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape from Ollama embed: {exc}") from exc
