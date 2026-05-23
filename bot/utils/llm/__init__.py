"""
LLM client package.

Public surface:
    get_llm_client(role) → LLMClient
    LLMClient             (ABC for type hints)
"""

from .base import LLMClient
from .registry import get_llm_client

__all__ = ["LLMClient", "get_llm_client"]
