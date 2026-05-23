"""
Pydantic boundary models — the typed contract between every module.

Rules:
- Every module boundary passes these models, never raw dicts.
- Models live here and only here; no submodule defines its own copies.
- MongoDB serialisation uses model_dump(mode="json") and model_validate().
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    DISCORD = "discord"
    TWITCH = "twitch"


# ---------------------------------------------------------------------------
# Message history
# ---------------------------------------------------------------------------

class Message(BaseModel):
    content: str
    from_bot: bool
    username: str
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


# ---------------------------------------------------------------------------
# User identity / state
# ---------------------------------------------------------------------------

class PlatformIdentity(BaseModel):
    user_id: str
    username: str
    nickname: Optional[str] = None
    display_name: str


class UserSummaries(BaseModel):
    relationship: str = "No additional information yet."
    last_conversation: str = "No conversation summary yet"
    last_updated: datetime = Field(default_factory=datetime.now)

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class UserState(BaseModel):
    """Full state for a single user, potentially spanning multiple platforms."""

    # platform name → identity on that platform (e.g. "discord" → PlatformIdentity)
    identifiers: dict[str, PlatformIdentity]
    primary_name: str
    name_variants: list[str]
    summaries: UserSummaries = Field(default_factory=UserSummaries)
    recent_messages: list[Message] = Field(default_factory=list)
    last_interaction: datetime = Field(default_factory=datetime.now)

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    @property
    def primary_platform(self) -> str:
        """Returns the first platform this user was registered under."""
        return next(iter(self.identifiers))

    @property
    def primary_identity(self) -> PlatformIdentity:
        return self.identifiers[self.primary_platform]


# ---------------------------------------------------------------------------
# Cone system
# ---------------------------------------------------------------------------

class ConeCondition(BaseModel):
    """A condition that, when met, automatically removes a cone."""
    type: str  # currently only "say_word"
    word: str
    variants: list[str]


class ConeData(BaseModel):
    """Persistent record of a cone applied to a user (keyed by Discord ID)."""
    effect: str
    active: bool
    applied_by: str
    reason: str
    timestamp: float
    expiry_time: Optional[float] = None
    condition: Optional[ConeCondition] = None
    duration_str: str = "permanent"
    target_username: str
    # Populated on deactivation:
    unconed_by: Optional[str] = None
    unconed_at: Optional[float] = None
    expired_at: Optional[float] = None
    condition_met_at: Optional[float] = None


class ConeResult(BaseModel):
    """Typed return value from every ConeManager operation."""
    success: bool
    message: str


# ---------------------------------------------------------------------------
# RAG retrieval (cross-module boundary types)
# ---------------------------------------------------------------------------

class RetrievalQuery(BaseModel):
    """
    Query passed from the pipeline handler to the RAG retriever.

    The router constructs this after classifying a user message as a lore/history query.
    Empty lists mean "no filter on this dimension" (match everything).
    """
    text: str                               # Original query text, used for embedding
    doc_types: list[str] = Field(default_factory=list)
    tags_must_include: list[str] = Field(default_factory=list)
    individuals_must_include: list[str] = Field(default_factory=list)
    min_significance: int = 1
    top_k: int = 5


class RetrievedChunk(BaseModel):
    """
    A single result returned by the retriever, ready for injection into Ghost's context.

    The `formatted` field is the pre-rendered string that gets appended to the system prompt.
    """
    chunk_id: str
    doc_type: str
    summary: str
    tags: list[str]
    individuals: list[str]
    significance: int
    event_date: Optional[str]
    score: float
    formatted: str  # Ready-to-inject context string
