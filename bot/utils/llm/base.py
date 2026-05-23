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

    async def embed(self, text: str) -> list[float]:
        """
        Generate a vector embedding for the given text.

        Only providers that support embeddings need to override this.
        The default raises NotImplementedError to surface misuse clearly.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support embeddings. "
            "Use the OllamaClient with role='embed' for embedding operations."
        )
