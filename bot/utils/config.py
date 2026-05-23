"""
YAML configuration loader.

All tunable values live in config.yaml at the project root.
Changing behaviour never requires editing Python code — only the YAML.

Usage:
    from bot.utils import get_config
    cfg = get_config()
    model_name = cfg.models.chat
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .exceptions import ConfigError


# ---------------------------------------------------------------------------
# Config dataclasses — one per YAML section
# ---------------------------------------------------------------------------

@dataclass
class ModelsConfig:
    chat: str = "gemini-2.5-flash-lite"
    vision: str = "gemini-2.0-flash"
    summary: str = "gemini-2.5-flash-lite"
    router: str = "gemma4:e4b"
    embedder: str = "nomic-embed-text"


@dataclass
class GeminiGenerationConfig:
    temperature: float = 0.9
    top_p: float = 0.7
    max_output_tokens: int = 1000


@dataclass
class GeminiConfig:
    chat: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.9, top_p=0.7, max_output_tokens=1000))
    vision: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.7, top_p=0.8, max_output_tokens=500))
    summary: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.3, top_p=0.9, max_output_tokens=500))


@dataclass
class MemoryConfig:
    message_history_limit: int = 15
    summary_trigger_count: int = 50
    messages_kept_after_summary: int = 30


@dataclass
class ConeConfig:
    default_duration_minutes: int = 30
    max_duration_hours: int = 24
    permissions: list[str] = field(default_factory=list)


@dataclass
class BotConfig:
    name: str = "Ghost"
    name_triggers: list[str] = field(default_factory=lambda: ["ghost", "ghosty"])
    daily_request_limit: int = 200
    minute_request_limit: int = 20
    nap_durations: dict[int, int] = field(default_factory=dict)


@dataclass
class DiscordConfig:
    max_message_length: int = 2000
    authorized_slash_user_ids: list[int] = field(default_factory=list)


@dataclass
class TwitchConfig:
    max_message_length: int = 500


@dataclass
class Config:
    models: ModelsConfig = field(default_factory=ModelsConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    cone: ConeConfig = field(default_factory=ConeConfig)
    bot: BotConfig = field(default_factory=BotConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    twitch: TwitchConfig = field(default_factory=TwitchConfig)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_config: Optional[Config] = None


def _find_config_path() -> Path:
    """Walk up from this file's location until we find config.yaml."""
    here = Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent, here.parent.parent.parent]:
        candidate = parent / "config.yaml"
        if candidate.exists():
            return candidate
    raise ConfigError(
        "config.yaml not found. Expected at the project root (ghost-bot/config.yaml)."
    )


def _load_config() -> Config:
    path = _find_config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse config.yaml: {exc}") from exc

    # --- models ---
    models_raw = raw.get("models", {})
    models = ModelsConfig(**{k: v for k, v in models_raw.items() if hasattr(ModelsConfig, k)}) if models_raw else ModelsConfig()

    # --- gemini ---
    def _gen_cfg(d: dict) -> GeminiGenerationConfig:
        return GeminiGenerationConfig(
            temperature=d.get("temperature", 0.9),
            top_p=d.get("top_p", 0.9),
            max_output_tokens=d.get("max_output_tokens", 1000),
        )
    gemini_raw = raw.get("gemini", {})
    gemini = GeminiConfig(
        chat=_gen_cfg(gemini_raw.get("chat", {})),
        vision=_gen_cfg(gemini_raw.get("vision", {})),
        summary=_gen_cfg(gemini_raw.get("summary", {})),
    )

    # --- memory ---
    memory_raw = raw.get("memory", {})
    memory = MemoryConfig(
        message_history_limit=memory_raw.get("message_history_limit", 15),
        summary_trigger_count=memory_raw.get("summary_trigger_count", 50),
        messages_kept_after_summary=memory_raw.get("messages_kept_after_summary", 30),
    )

    # --- cone ---
    cone_raw = raw.get("cone", {})
    cone = ConeConfig(
        default_duration_minutes=cone_raw.get("default_duration_minutes", 30),
        max_duration_hours=cone_raw.get("max_duration_hours", 24),
        permissions=[p.lower() for p in cone_raw.get("permissions", [])],
    )

    # --- bot ---
    bot_raw = raw.get("bot", {})
    nap_raw = bot_raw.get("nap_durations", {})
    bot = BotConfig(
        name=bot_raw.get("name", "Ghost"),
        name_triggers=[t.lower() for t in bot_raw.get("name_triggers", ["ghost", "ghosty"])],
        daily_request_limit=bot_raw.get("daily_request_limit", 200),
        minute_request_limit=bot_raw.get("minute_request_limit", 20),
        nap_durations={int(k): int(v) for k, v in nap_raw.items()},
    )

    # --- discord ---
    discord_raw = raw.get("discord", {})
    discord = DiscordConfig(
        max_message_length=discord_raw.get("max_message_length", 2000),
        authorized_slash_user_ids=[int(i) for i in discord_raw.get("authorized_slash_user_ids", [])],
    )

    # --- twitch ---
    twitch_raw = raw.get("twitch", {})
    twitch = TwitchConfig(
        max_message_length=twitch_raw.get("max_message_length", 500),
    )

    return Config(
        models=models,
        gemini=gemini,
        memory=memory,
        cone=cone,
        bot=bot,
        discord=discord,
        twitch=twitch,
    )


def get_config() -> Config:
    """Return the singleton Config, loading from YAML on first call."""
    global _config
    if _config is None:
        _config = _load_config()
    return _config
