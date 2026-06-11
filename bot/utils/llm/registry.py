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
    "router"        → OllamaClient (models.router)        — Phase 5
    "rag_planner"   → OllamaClient (models.rag_planner)  — Phase 5
    "cone_approval" → OllamaClient (models.cone_approval) — Phase 5
    "embed"         → OllamaClient (models.embedder)      — Phase 4
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
        api_key_free = os.environ.get("GEMINI_API_KEY")
        if not api_key_free:
            raise ConfigError("GEMINI_API_KEY environment variable is not set.")

        api_key_paid = os.environ.get("GEMINI_API_KEY_PAID") or None
        preferred_source = cfg.models.api_keys.get(role, "free")

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
            api_key_free=api_key_free,
            api_key_paid=api_key_paid,
            preferred_source=preferred_source,
            role=role,
            model=model,
            temperature=gen.temperature,
            top_p=gen.top_p,
            max_output_tokens=gen.max_output_tokens,
            enable_web_grounding=cfg.gemini.enable_web_grounding if role == "chat" else False,
        )

    if role in ("router", "rag_planner", "cone_approval"):
        if role == "router":
            model = cfg.models.router
            gen = cfg.ollama.router
        elif role == "rag_planner":
            model = cfg.models.rag_planner
            gen = cfg.ollama.rag_planner
        else:  # cone_approval
            model = cfg.models.cone_approval
            gen = cfg.ollama.cone_approval

        if model.startswith(("gemini-", "gemma-")):
            api_key_free = os.environ.get("GEMINI_API_KEY", "")
            api_key_paid = os.environ.get("GEMINI_API_KEY_PAID") or None

            thinking_budget = None
            if gen.think is False or gen.think == 0:
                thinking_budget = 0
            elif gen.think == "low":
                thinking_budget = 1024
            elif isinstance(gen.think, int):
                thinking_budget = gen.think

            return GeminiClient(
                api_key_free=api_key_free,
                api_key_paid=api_key_paid,
                preferred_source="free",
                role=role,
                model=model,
                temperature=gen.temperature,
                top_p=0.9,
                max_output_tokens=gen.num_predict,
                thinking_budget=thinking_budget,
            )
        else:
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            return OllamaClient(
                model=model,
                base_url=ollama_url,
                temperature=gen.temperature,
                num_predict=gen.num_predict,
                role=role,
                think=gen.think,
                keep_alive=gen.keep_alive,
            )

    if role == "embed":
        # Phase 4 — nomic-embed-large via Ollama
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaClient(model=cfg.models.embedder, base_url=ollama_url, role=role, keep_alive=-1)

    raise ConfigError(
        f"Unknown LLM role '{role}'. Valid roles: chat, vision, summary, "
        "extractor, arc_summarizer, router, rag_planner, cone_approval, embed."
    )
