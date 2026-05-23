"""
Internal Pydantic models for the RAG pipeline.

These models are internal to the memory.rag package.
Cross-module boundary types (RetrievalQuery, RetrievedChunk) live in bot.utils.models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DocType(str, Enum):
    CONVERSATION = "conversation"
    LORE = "lore"
    EVENT = "event"
    FACT = "fact"
    CHARACTER_DEVELOPMENT = "character_development"
    RELATIONSHIP = "relationship"
    WORLDBUILDING = "worldbuilding"
    DECISIONS = "decisions"
    MYSTERIES = "mysteries"
    ARC_SUMMARY = "arc_summary"
    OTHERS = "others"


class ChunkStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    SUMMARIZED = "summarized"


class Sentiment(str, Enum):
    LIGHT = "light"
    TENSE = "tense"
    DRAMATIC = "dramatic"
    HUMOROUS = "humorous"
    EMOTIONAL = "emotional"


# ---------------------------------------------------------------------------
# Core document model
# ---------------------------------------------------------------------------

class RAGDocument(BaseModel):
    """
    A single memory chunk stored in the rag_documents MongoDB collection.

    Every field maps directly to the schema defined in the architecture plan.
    The embedding field is populated by the embedder after extraction.
    """

    id: str                                         # Unique chunk ID (uuid4)
    doc_type: DocType
    suggested_doc_type: Optional[str] = None        # Only set when doc_type == "others"

    summary: str                                    # 2-4 sentence LLM-generated abstract
    key_quotes: list[str] = Field(default_factory=list)  # 0-3 verbatim quotes

    # Tag layers
    tags: list[str] = Field(default_factory=list)                       # Approved namespaced tags
    suggested_tags: list[str] = Field(default_factory=list)             # Pending human review
    suggestion_justifications: dict[str, str] = Field(default_factory=dict)  # tag → reason
    free_labels: list[str] = Field(default_factory=list)                # 3-5 unconstrained keywords

    # Core structural (Layer 1 — always present)
    individuals: list[str] = Field(default_factory=list)
    significance: int                               # 1-5
    sentiment: Sentiment

    # Validity / lifecycle
    status: ChunkStatus = ChunkStatus.ACTIVE
    supersedes_id: Optional[str] = None             # ID of the chunk this one replaces
    related_chunk_ids: list[str] = Field(default_factory=list)
    potential_contradiction: bool = False           # Flagged during ingestion; requires human review

    # Temporal
    event_date: Optional[str] = None                # ISO date string, estimated by extractor
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    source_channel_id: str
    source_message_ids: list[str] = Field(default_factory=list)

    # Vector
    embedding: list[float] = Field(default_factory=list)
    is_summarized: bool = False                     # True once covered by an arc_summary chunk

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    def embedding_text(self) -> str:
        """Canonical text used for generating the embedding vector."""
        label_str = " ".join(self.free_labels)
        return f"{self.summary} {label_str}".strip()

    def format_for_context(self) -> str:
        """
        Render this chunk as the injected context string Ghost sees in her system prompt.

        Format:
            [MEMORY: {doc_type} | {first arc tag} | significance:{n} | {event_date or ingested_at}]
            {summary}
            {key quotes if any}
        """
        arc_tags = [t for t in self.tags if t.startswith("arc:")]
        arc_str = arc_tags[0] if arc_tags else "general"
        date_str = self.event_date or self.ingested_at.strftime("%Y-%m-%d")
        header = f"[MEMORY: {self.doc_type} | {arc_str} | significance:{self.significance} | {date_str}]"
        parts = [header, self.summary]
        if self.key_quotes:
            parts.append("Notable quotes: " + " / ".join(f'"{q}"' for q in self.key_quotes))
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Ingestion intermediate types
# ---------------------------------------------------------------------------

class RawMessage(BaseModel):
    """A single Discord message as fetched during ingestion."""
    message_id: str
    author_name: str
    author_id: str
    content: str
    timestamp: datetime
    is_bot: bool

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class MessageSegment(BaseModel):
    """A group of consecutive messages forming a coherent conversation unit."""
    messages: list[RawMessage]
    channel_id: str

    @property
    def message_ids(self) -> list[str]:
        return [m.message_id for m in self.messages]

    @property
    def start_time(self) -> datetime:
        return self.messages[0].timestamp

    @property
    def end_time(self) -> datetime:
        return self.messages[-1].timestamp

    def format_for_prompt(self) -> str:
        """Render messages as a readable transcript for the extractor LLM."""
        lines = []
        for msg in self.messages:
            ts = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            lines.append(f"[{ts}] {msg.author_name}: {msg.content}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extractor output
# ---------------------------------------------------------------------------

class ExtractionResult(BaseModel):
    """
    The structured JSON the extractor LLM returns for a single MessageSegment.

    If worth_storing is False, all other fields are ignored.
    Validated against the JSON the LLM generates — if parsing fails, the segment is skipped
    and the error is logged for investigation.
    """
    worth_storing: bool
    doc_type: Optional[DocType] = None
    suggested_doc_type: Optional[str] = None
    summary: Optional[str] = None
    key_quotes: list[str] = Field(default_factory=list)
    individuals: list[str] = Field(default_factory=list)
    significance: Optional[int] = None
    sentiment: Optional[Sentiment] = None
    tags: list[str] = Field(default_factory=list)
    suggested_tags: list[str] = Field(default_factory=list)
    suggestion_justifications: dict[str, str] = Field(default_factory=dict)
    free_labels: list[str] = Field(default_factory=list)
    event_date: Optional[str] = None
    related_chunk_ids: list[str] = Field(default_factory=list)


class SegmentExtractionResult(ExtractionResult):
    """
    One entry in the batch extraction response.

    Extends ExtractionResult with the segment_index so the extractor can
    map results back to segments even if the LLM skips some indices.
    """
    segment_index: int


class BatchExtractionResult(BaseModel):
    """
    The top-level JSON object returned by the batch extractor LLM call.

    The LLM produces exactly one of these per ingestion run, containing
    one SegmentExtractionResult for every segment it decided is worth storing
    (or explicitly marking worth_storing=false for those it skips).
    Missing indices are treated as not worth storing.
    """
    extractions: list[SegmentExtractionResult]


# ---------------------------------------------------------------------------
# Contradiction checker output
# ---------------------------------------------------------------------------

class ContradictionCheckResult(BaseModel):
    """The structured JSON from the contradiction checker LLM."""
    contradiction_detected: bool
    contradicted_chunk_id: Optional[str] = None
    explanation: str


# ---------------------------------------------------------------------------
# Arc summary trigger state
# ---------------------------------------------------------------------------

class ArcTagStats(BaseModel):
    """Aggregated stats for a single arc tag, used to decide if summarisation is needed."""
    arc_tag: str
    active_chunk_count: int
    estimated_total_tokens: int       # Rough estimate: sum of len(summary) / 4
    last_ingested_at: Optional[datetime] = None
    has_existing_summary: bool = False

    @property
    def days_since_last_ingestion(self) -> Optional[float]:
        if self.last_ingested_at is None:
            return None
        delta = datetime.utcnow() - self.last_ingested_at
        return delta.total_seconds() / 86400


# ---------------------------------------------------------------------------
# Ingestion run report
# ---------------------------------------------------------------------------

class IngestionReport(BaseModel):
    """Summary of a completed ingestion run, for logging."""
    run_at: datetime = Field(default_factory=datetime.utcnow)
    channels_processed: int = 0
    segments_found: int = 0
    segments_skipped_duplicate: int = 0
    segments_skipped_not_worth_storing: int = 0
    segments_extraction_failed: int = 0
    chunks_stored: int = 0
    contradictions_flagged: int = 0
    arc_summaries_triggered: list[str] = Field(default_factory=list)

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}
