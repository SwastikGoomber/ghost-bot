"""
Ghost Bot exception hierarchy.

Catch GhostError to handle any bot-level failure.
Catch specific subclasses for fine-grained handling.
"""


class GhostError(Exception):
    """Base exception for all Ghost Bot errors."""


class ConfigError(GhostError):
    """Raised when configuration is missing, malformed, or invalid."""


class LLMError(GhostError):
    """Raised when an LLM API call fails."""


class LLMRateLimitError(LLMError):
    """Raised specifically when an LLM provider returns a rate-limit (429) response."""


class ConeError(GhostError):
    """Raised when a cone operation fails."""


class ConeEffectNotFoundError(ConeError):
    """Raised when a requested cone effect name does not exist in the registry."""


class StateError(GhostError):
    """Raised when a user-state operation fails."""


class DatabaseError(GhostError):
    """Raised when a database read/write operation fails."""
