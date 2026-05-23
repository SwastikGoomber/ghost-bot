"""
Abstract base class for all LLM clients.

Every provider (Gemini, Ollama, …) implements this contract.
Callers depend only on LLMClient — never on a concrete class.
"""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Minimal contract every LLM provider must implement."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        """
        Generate a text response.

        Args:
            messages:     Conversation history as [{"role": "user"|"model", "content": str}, …]
            system_prompt: Instructions prepended as system context.

        Returns:
            The model's text response.
        """
        ...
