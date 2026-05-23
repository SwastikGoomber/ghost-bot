"""
Ollama LLM client — Phase 3 stub.

This will be fully implemented when the Gemma 4 router is wired in (Phase 3).
Instantiating it now raises NotImplementedError so misconfiguration is loud.
"""

from .base import LLMClient
from ..exceptions import LLMError


class OllamaClient(LLMClient):
    """Client for local Ollama models (Gemma 4 router, nomic embedder)."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        raise NotImplementedError(
            "OllamaClient.generate() is not implemented yet — this is a Phase 3 feature. "
            "If you are seeing this error in production, the router config is wrong."
        )
