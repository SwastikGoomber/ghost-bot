"""
RAG embedder — wraps the OllamaClient embed() call for RAG-specific usage.

The embedder's job is simple: take a string and return a list[float].
It enforces the "fail hard if Ollama is unavailable" policy — no graceful
degradation, because a chunk stored without an embedding is useless for
retrieval and silently breaks the pipeline.

Usage:
    from bot.memory.rag.embedder import embed_text

    vector = await embed_text("The crew discovered an abandoned station...")
"""

from __future__ import annotations

import logging

from bot.utils.llm.registry import get_llm_client
from bot.utils.llm.ollama import OllamaClient
from bot.utils.exceptions import LLMError

logger = logging.getLogger(__name__)


async def embed_text(text: str) -> list[float]:
    """
    Generate an embedding vector for the given text via Ollama nomic-embed-text.

    This is intentionally thin — all error handling is surfaced to the caller
    so the ingestion pipeline can log the failure and abort cleanly.

    Args:
        text: The text to embed. For RAG chunks, this is doc.embedding_text().

    Returns:
        A list of floats (768 dimensions for nomic-embed-text).

    Raises:
        LLMError: If Ollama is unreachable or returns an error.
                  Ingestion will abort on this — Ollama must be running.
    """
    client = get_llm_client("embed")
    if not isinstance(client, OllamaClient):
        raise LLMError(
            "The 'embed' role must map to an OllamaClient. "
            "Check registry.py configuration."
        )
    vector = await client.embed(text)
    logger.debug("Embedded %d chars → vector dim=%d", len(text), len(vector))
    return vector
