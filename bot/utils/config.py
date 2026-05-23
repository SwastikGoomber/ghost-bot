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
    cone_approval: str = "gemma4:e4b"
    rag_planner: str = "gemma4:e4b"
    embedder: str = "nomic-embed-text"
    extractor: str = "gemini-2.5-flash"
    arc_summarizer: str = "gemini-2.5-flash"


@dataclass
class GeminiGenerationConfig:
    temperature: float = 0.9
    top_p: float = 0.7
    max_output_tokens: int = 1000


@dataclass
class OllamaGenerationConfig:
    temperature: float = 0.1
    num_predict: int = 128  # Ollama's equivalent of max_output_tokens


@dataclass
class GeminiConfig:
    chat: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.9, top_p=0.7, max_output_tokens=1000))
    vision: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.7, top_p=0.8, max_output_tokens=500))
    summary: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.3, top_p=0.9, max_output_tokens=500))
    extraction: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.1, top_p=0.9, max_output_tokens=2000))
    arc_summary: GeminiGenerationConfig = field(default_factory=lambda: GeminiGenerationConfig(temperature=0.5, top_p=0.9, max_output_tokens=1500))


@dataclass
class OllamaConfig:
    router: OllamaGenerationConfig = field(default_factory=lambda: OllamaGenerationConfig(temperature=0.1, num_predict=64))
    rag_planner: OllamaGenerationConfig = field(default_factory=lambda: OllamaGenerationConfig(temperature=0.2, num_predict=512))
    cone_approval: OllamaGenerationConfig = field(default_factory=lambda: OllamaGenerationConfig(temperature=0.2, num_predict=128))


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
    # Programmatic gate thresholds (Tier 0)
    per_target_cooldown_minutes: int = 60
    hourly_limit: int = 5
    autonomous_max_per_day: int = 2


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
class RagConfig:
    enabled: bool = False
    enabled_channel_ids: list[int] = field(default_factory=list)
    extraction_cron: str = "0 30 0 * * *"
    extraction_lookback_hours: int = 24
    min_message_length_words: int = 5
    conversation_gap_minutes: int = 10
    arc_summary_token_threshold: int = 4000
    arc_closure_gap_days: int = 5
    retrieval_top_k: int = 5
    vector_weight: float = 0.6
    significance_weight: float = 0.4
    min_significance_filter: int = 1
    suggested_tag_collection: str = "rag_suggested_tags"
    post_filter_disabled: bool = False  # Set true to skip $match post-filter (debug only)


@dataclass
class Config:
    models: ModelsConfig = field(default_factory=ModelsConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    cone: ConeConfig = field(default_factory=ConeConfig)
    bot: BotConfig = field(default_factory=BotConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    twitch: TwitchConfig = field(default_factory=TwitchConfig)
    rag: RagConfig = field(default_factory=RagConfig)


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
    def _gen_cfg(d: dict, default_temp: float = 0.9, default_max: int = 1000) -> GeminiGenerationConfig:
        return GeminiGenerationConfig(
            temperature=d.get("temperature", default_temp),
            top_p=d.get("top_p", 0.9),
            max_output_tokens=d.get("max_output_tokens", default_max),
        )
    gemini_raw = raw.get("gemini", {})
    gemini = GeminiConfig(
        chat=_gen_cfg(gemini_raw.get("chat", {}), default_temp=0.9, default_max=1000),
        vision=_gen_cfg(gemini_raw.get("vision", {}), default_temp=0.7, default_max=500),
        summary=_gen_cfg(gemini_raw.get("summary", {}), default_temp=0.3, default_max=500),
        extraction=_gen_cfg(gemini_raw.get("extraction", {}), default_temp=0.1, default_max=2000),
        arc_summary=_gen_cfg(gemini_raw.get("arc_summary", {}), default_temp=0.5, default_max=1500),
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
        per_target_cooldown_minutes=int(cone_raw.get("per_target_cooldown_minutes", 60)),
        hourly_limit=int(cone_raw.get("hourly_limit", 5)),
        autonomous_max_per_day=int(cone_raw.get("autonomous_max_per_day", 2)),
    )

    # --- ollama ---
    def _ollama_cfg(d: dict, default_temp: float = 0.1, default_predict: int = 128) -> OllamaGenerationConfig:
        return OllamaGenerationConfig(
            temperature=d.get("temperature", default_temp),
            num_predict=d.get("num_predict", default_predict),
        )
    ollama_raw = raw.get("ollama", {})
    ollama = OllamaConfig(
        router=_ollama_cfg(ollama_raw.get("router", {}), default_temp=0.1, default_predict=64),
        rag_planner=_ollama_cfg(ollama_raw.get("rag_planner", {}), default_temp=0.2, default_predict=512),
        cone_approval=_ollama_cfg(ollama_raw.get("cone_approval", {}), default_temp=0.2, default_predict=128),
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

    # --- rag ---
    rag_raw = raw.get("rag", {})
    rag = RagConfig(
        enabled=rag_raw.get("enabled", False),
        enabled_channel_ids=[int(i) for i in rag_raw.get("enabled_channel_ids", [])],
        extraction_cron=rag_raw.get("extraction_cron", "0 30 0 * * *"),
        extraction_lookback_hours=int(rag_raw.get("extraction_lookback_hours", 24)),
        min_message_length_words=int(rag_raw.get("min_message_length_words", 5)),
        conversation_gap_minutes=int(rag_raw.get("conversation_gap_minutes", 10)),
        arc_summary_token_threshold=int(rag_raw.get("arc_summary_token_threshold", 4000)),
        arc_closure_gap_days=int(rag_raw.get("arc_closure_gap_days", 5)),
        retrieval_top_k=int(rag_raw.get("retrieval_top_k", 5)),
        vector_weight=float(rag_raw.get("vector_weight", 0.6)),
        significance_weight=float(rag_raw.get("significance_weight", 0.4)),
        min_significance_filter=int(rag_raw.get("min_significance_filter", 1)),
        suggested_tag_collection=str(rag_raw.get("suggested_tag_collection", "rag_suggested_tags")),
    )

    return Config(
        models=models,
        gemini=gemini,
        ollama=ollama,
        memory=memory,
        cone=cone,
        bot=bot,
        discord=discord,
        twitch=twitch,
        rag=rag,
    )


def get_config() -> Config:
    """Return the singleton Config, loading from YAML on first call."""
    global _config
    if _config is None:
        _config = _load_config()
    return _config
