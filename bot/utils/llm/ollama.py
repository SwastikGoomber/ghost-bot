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

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

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
                    return data["message"]["content"]
        except aiohttp.ClientConnectorError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Is Ollama running? (ollama serve)"
            ) from exc
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape from Ollama: {exc}") from exc

    # ------------------------------------------------------------------
    # Embeddings — /api/embed
    # ------------------------------------------------------------------

    async def embed(self, text: str) -> list[float]:
        """
        Generate a vector embedding for the given text.

        Uses Ollama's /api/embed endpoint with the model configured for this client.
        For the RAG pipeline, this client is initialised with model="nomic-embed-large".
        Returns 1024-dimensional vectors.

        Args:
            text: The text to embed (typically: summary + space-joined free_labels).

        Returns:
            A flat list of floats (1024 dimensions for nomic-embed-large).

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
                "Is Ollama running with nomic-embed-large pulled? "
                "(ollama serve && ollama pull nomic-embed-large)"
            ) from exc
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected response shape from Ollama embed: {exc}") from exc
