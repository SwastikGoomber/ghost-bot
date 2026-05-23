"""
LLM client factory.

The registry is the single point where LLM clients are instantiated.
Feature modules call get_llm_client(role) and get back a configured client —
they never touch API keys or model names directly.

Roles:
    "chat"          → GeminiClient (models.chat, chat generation config)
    "vision"        → GeminiClient (models.vision, vision generation config)
    "summary"       → GeminiClient (models.summary, summary generation config)
    "extractor"     → GeminiClient (models.extractor, extraction config) — Phase 4 RAG
    "arc_summarizer"→ GeminiClient (models.arc_summarizer, arc_summary config) — Phase 4 RAG
    "router"        → OllamaClient (models.router)   — Phase 3
    "embed"         → OllamaClient (models.embedder) — Phase 4
"""

from __future__ import annotations

import os
from functools import lru_cache

from ..exceptions import ConfigError
from .base import LLMClient
from .gemini import GeminiClient
from .ollama import OllamaClient


def get_llm_client(role: str) -> LLMClient:
    """
    Return a configured LLMClient for the given role.

    Clients are cached by role (singleton per role per process lifetime).
    """
    return _get_cached_client(role)


@lru_cache(maxsize=None)
def _get_cached_client(role: str) -> LLMClient:
    from ..config import get_config
    cfg = get_config()

    if role in ("chat", "vision", "summary", "extractor", "arc_summarizer"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ConfigError("GEMINI_API_KEY environment variable is not set.")

        if role == "chat":
            gen = cfg.gemini.chat
            model = cfg.models.chat
        elif role == "vision":
            gen = cfg.gemini.vision
            model = cfg.models.vision
        elif role == "summary":
            gen = cfg.gemini.summary
            model = cfg.models.summary
        elif role == "extractor":
            gen = cfg.gemini.extraction
            model = cfg.models.extractor
        else:  # arc_summarizer
            gen = cfg.gemini.arc_summary
            model = cfg.models.arc_summarizer

        return GeminiClient(
            api_key=api_key,
            model=model,
            temperature=gen.temperature,
            top_p=gen.top_p,
            max_output_tokens=gen.max_output_tokens,
        )

    if role == "router":
        # Phase 3 — Gemma 4 via Ollama
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaClient(model=cfg.models.router, base_url=ollama_url)

    if role == "embed":
        # Phase 4 — nomic-embed-text via Ollama
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaClient(model=cfg.models.embedder, base_url=ollama_url)

    raise ConfigError(
        f"Unknown LLM role '{role}'. Valid roles: chat, vision, summary, "
        "extractor, arc_summarizer, router, embed."
    )
