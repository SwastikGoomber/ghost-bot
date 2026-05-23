"""
Shared utilities — the single source of truth for config, models, exceptions, logging, and LLM clients.
Nothing outside this package should be imported from sub-modules directly;
import from `bot.utils` only.
"""

from .config import get_config, Config
from .exceptions import (
    GhostError,
    ConfigError,
    LLMError,
    LLMRateLimitError,
    ConeError,
    ConeEffectNotFoundError,
    StateError,
    DatabaseError,
)
from .models import (
    Platform,
    Message,
    ChannelContextMessage,
    PlatformIdentity,
    UserSummaries,
    UserState,
    NameAliasMap,
    ConeCondition,
    ConeData,
    ConeResult,
)
from .name_resolution import build_name_alias_map
from .logging import setup_logging, get_logger
from .llm import get_llm_client, LLMClient

__all__ = [
    # config
    "get_config",
    "Config",
    # exceptions
    "GhostError",
    "ConfigError",
    "LLMError",
    "LLMRateLimitError",
    "ConeError",
    "ConeEffectNotFoundError",
    "StateError",
    "DatabaseError",
    # models
    "Platform",
    "Message",
    "ChannelContextMessage",
    "PlatformIdentity",
    "UserSummaries",
    "UserState",
    "NameAliasMap",
    "ConeCondition",
    "ConeData",
    "ConeResult",
    "build_name_alias_map",
    # logging
    "setup_logging",
    "get_logger",
    # llm
    "get_llm_client",
    "LLMClient",
]
