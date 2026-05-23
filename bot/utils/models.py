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
from typing import Literal, Optional

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


class ChannelContextMessage(BaseModel):
    """
    Recent ambient channel message passed from a platform adapter to the pipeline.

    This is prompt context only; it is not persisted as user memory.
    """
    content: str
    username: str
    timestamp: datetime = Field(default_factory=datetime.now)
    from_bot: bool = False
    user_id: Optional[str] = None

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

    # User-set profile fields (managed via /ghost set commands)
    aliases: list[str] = Field(default_factory=list)    # alternate names / nicknames
    pronouns: list[str] = Field(default_factory=list)   # e.g. ["she/her", "they/them"]
    bio: str = ""                                        # free-text paragraph about themselves

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


class ConeToolCall(BaseModel):
    """
    Parsed cone intent from Ghost's initiate_cone tool call.

    Represents what Ghost wants to do — NOT Ghost's response.
    Response is generated reactively after the pipeline runs.
    """
    cone_target: str
    cone_effect: str
    cone_trigger: str                   # "requested_approved" | "requested_unapproved" | "autonomous"
    cone_duration: Optional[str] = None  # e.g. "30 minutes"; None = Ghost's discretion
    cone_condition: Optional[str] = None # e.g. "until they say sorry"


class ConeOutcome(BaseModel):
    """
    Result of the full cone pipeline.

    Passed back to Gemini as a function_response so Ghost can react
    to what actually happened (applied, denied, error) in its own voice.
    """
    status: Literal["applied", "denied", "target_unknown", "apply_failed", "error"]
    target: str
    effect: Optional[str] = None
    duration: Optional[str] = None
    condition: Optional[str] = None
    reason: str   # Approval agent reason, or error description



# ---------------------------------------------------------------------------
# RAG retrieval (cross-module boundary types)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Phase 5: Router + RAG Planner + Cone approval boundary models
# ---------------------------------------------------------------------------

class RouterFlags(BaseModel):
    """
    Output of the IntentRouter (Gemma 4 via Ollama).

    Each flag is independent — multiple can be True simultaneously.
    Both False = pure casual chat, call Gemini in text mode with no extra context.
    """
    rag_required: bool = False    # Message references past events, lore, people, history
    cone_relevant: bool = False   # Someone is EXPLICITLY asking for a cone right now


class LogicGate(str, Enum):
    """Filter combinators for RetrievalQuery clauses, maps to MongoDB operators."""
    AND = "AND"   # All values must be present  → $all
    OR  = "OR"    # Any value must be present   → $in
    NOT = "NOT"   # No values must be present   → $nin


class FilterClause(BaseModel):
    """A typed filter for a single RAG dimension (individuals, arc tags, doc types)."""
    values: list[str]
    gate: LogicGate = LogicGate.OR


class RetrievalQuery(BaseModel):
    """
    Query passed from the RAG planner to the retriever.

    Supports logic gates (AND/OR/NOT) per dimension for precise pre-filtering.
    Empty / None clause means "no filter on this dimension" (match everything).
    """
    query_text: str                                # Semantic search string (may differ from raw message)
    individual_filter: Optional[FilterClause] = None   # e.g., AND ["ghost", "lilly"]
    arc_tag_filter: Optional[FilterClause] = None      # e.g., OR ["arc:origin", "arc:heist"]
    doc_type_filter: Optional[FilterClause] = None     # e.g., OR ["event", "lore"]
    exclude_individuals: list[str] = Field(default_factory=list)  # Always $nin
    min_significance: int = 1
    time_range_start: Optional[str] = None         # ISO date string
    time_range_end: Optional[str] = None
    top_k: int = 5


class ConeApprovalResult(BaseModel):
    """Output of the Tier 1 Gemma 4 cone approval agent."""
    approved: bool
    reason: str    # Logged only — never shown to users


class TaxonomySnapshot(BaseModel):
    """
    Cached snapshot of the RAG vector DB taxonomy.

    Built once at startup (and refreshed after each ingestion run).
    Injected into the RAG Query Planner's prompt so it can filter precisely.
    """
    arc_tags: dict[str, int] = Field(default_factory=dict)        # {"arc:ghost-origin": 34, ...}
    doc_type_counts: dict[str, int] = Field(default_factory=dict) # {"fact": 89, ...}
    known_individuals: list[str] = Field(default_factory=list)
    known_locations: list[str] = Field(default_factory=list)
    known_topics: list[str] = Field(default_factory=list)


class NameAliasMap(BaseModel):
    """
    Alias expansion boundary shared with RAG.

    Keys are normalized names/aliases. Values are every known spelling for the
    same user, preserving original casing where available.
    """
    aliases_by_name: dict[str, list[str]] = Field(default_factory=dict)

    def expand(self, name: str) -> list[str]:
        normalized = " ".join(name.lower().split())
        return self.aliases_by_name.get(normalized, [])


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
