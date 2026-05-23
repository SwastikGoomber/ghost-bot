"""
RAG retriever — hybrid metadata filter + vector similarity + significance weighting.

Retrieval flow (per the architecture plan):
    1. Embed the query text via Ollama nomic-embed-text
    2. Run Atlas Vector Search with metadata pre-filter
    3. Apply significance weighting to re-rank results
    4. Deduplicate: if multiple chunks are covered by an arc_summary, prefer the summary
    5. Return top-K RetrievedChunk objects, ready for injection into Ghost's context

The retriever is called by the pipeline handler when the router determines that
an incoming message requires lore/history context (Phase 3 + 4 integration).

Until Phase 3 (router) is implemented, callers can construct a RetrievalQuery manually
and call retrieve() directly.
"""

from __future__ import annotations

import logging
from typing import Optional

from bot.utils.config import get_config
from bot.utils.models import RetrievalQuery, RetrievedChunk
from bot.utils.exceptions import LLMError

from .embedder import embed_text
from .models import DocType, RAGDocument
from .store import vector_search, metadata_only_search

logger = logging.getLogger(__name__)


async def retrieve(query: RetrievalQuery) -> list[RetrievedChunk]:
    """
    Execute a hybrid retrieval query and return ranked, formatted results.

    This is the primary public API of the retriever.

    Args:
        query: Structured retrieval query (from pipeline handler or Phase 3 router).

    Returns:
        Up to query.top_k RetrievedChunk objects, sorted by final score descending.
        Returns an empty list if no results are found or if retrieval fails.
    """
    cfg = get_config()
    top_k = query.top_k or cfg.rag.retrieval_top_k

    # Embed the query text
    try:
        query_embedding = await embed_text(query.text)
    except LLMError as exc:
        logger.error("Retrieval embedding failed: %s. Falling back to metadata-only search.", exc)
        query_embedding = None

    # Fetch candidates
    if query_embedding is not None:
        raw_docs = await vector_search(
            query_embedding=query_embedding,
            doc_types=query.doc_types,
            tags_must_include=query.tags_must_include,
            individuals_must_include=query.individuals_must_include,
            min_significance=query.min_significance,
            num_candidates=min(top_k * 20, 200),
            limit=top_k * 4,
        )
    else:
        raw_docs = await metadata_only_search(
            doc_types=query.doc_types,
            tags_must_include=query.tags_must_include,
            individuals_must_include=query.individuals_must_include,
            min_significance=query.min_significance,
            limit=top_k * 4,
        )

    if not raw_docs:
        logger.debug("Retrieval returned 0 candidates for query: %.80s", query.text)
        return []

    # Parse into RAGDocument objects
    parsed: list[tuple[RAGDocument, float]] = []
    for raw in raw_docs:
        raw["id"] = raw.pop("_id", raw.get("id", ""))
        vector_score = float(raw.pop("vector_score", 0.0))
        try:
            doc = RAGDocument.model_validate(raw)
            parsed.append((doc, vector_score))
        except Exception as exc:
            logger.warning("Failed to parse retrieval result: %s", exc)

    # Apply combined scoring
    scored = _apply_scoring(parsed, cfg.rag.vector_weight, cfg.rag.significance_weight)

    # Deduplicate: prefer arc_summary over individual chunks it covers
    deduplicated = _deduplicate_summarized(scored)

    # Take top K
    top = deduplicated[:top_k]

    # Convert to RetrievedChunk
    results = []
    for doc, score in top:
        results.append(RetrievedChunk(
            chunk_id=doc.id,
            doc_type=doc.doc_type.value,
            summary=doc.summary,
            tags=doc.tags,
            individuals=doc.individuals,
            significance=doc.significance,
            event_date=doc.event_date,
            score=round(score, 4),
            formatted=doc.format_for_context(),
        ))

    logger.debug("Retrieval returned %d results for query: %.80s", len(results), query.text)
    return results


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _apply_scoring(
    candidates: list[tuple[RAGDocument, float]],
    vector_weight: float,
    significance_weight: float,
) -> list[tuple[RAGDocument, float]]:
    """
    Combine vector similarity and significance into a single score and re-sort.

    Final score = (vector_score * vector_weight) + (significance_normalised * significance_weight)

    Significance is normalised from [1,5] to [0,1]: (significance - 1) / 4
    """
    scored = []
    for doc, vector_score in candidates:
        significance_norm = (doc.significance - 1) / 4.0
        combined = (vector_score * vector_weight) + (significance_norm * significance_weight)
        scored.append((doc, combined))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# Deduplication: prefer arc_summary over individual summarized chunks
# ---------------------------------------------------------------------------

def _deduplicate_summarized(
    scored: list[tuple[RAGDocument, float]],
) -> list[tuple[RAGDocument, float]]:
    """
    If an arc_summary and individual chunks from the same arc are both in the result set,
    prefer the arc_summary and drop is_summarized=True individual chunks.

    Arc summaries already contain the narrative of all their source chunks.
    Returning both would be redundant context.

    Individual chunks that are NOT yet summarised (is_summarized=False) are always kept.
    """
    # Find all arc tags that have an arc_summary in the result set
    arcs_with_summary: set[str] = set()
    for doc, _ in scored:
        if doc.doc_type == DocType.ARC_SUMMARY:
            arc_tags = [t for t in doc.tags if t.startswith("arc:")]
            arcs_with_summary.update(arc_tags)

    if not arcs_with_summary:
        return scored

    deduped = []
    for doc, score in scored:
        if doc.doc_type == DocType.ARC_SUMMARY:
            deduped.append((doc, score))
            continue

        if not doc.is_summarized:
            deduped.append((doc, score))
            continue

        # This chunk is summarized — check if its arc is already represented by a summary
        chunk_arc_tags = [t for t in doc.tags if t.startswith("arc:")]
        covered = any(t in arcs_with_summary for t in chunk_arc_tags)
        if not covered:
            deduped.append((doc, score))
        # else: drop — the arc_summary covers it

    return deduped


# ---------------------------------------------------------------------------
# Convenience: format retrieved chunks for injection
# ---------------------------------------------------------------------------

def format_for_injection(chunks: list[RetrievedChunk]) -> str:
    """
    Format a list of retrieved chunks into a single block for Ghost's system prompt.

    Each chunk is separated by a blank line. The block is wrapped with clear delimiters
    so Ghost knows this is retrieved memory, not real-time conversation.
    """
    if not chunks:
        return ""

    parts = ["[RETRIEVED MEMORIES — use these to inform your response]"]
    for chunk in chunks:
        parts.append(chunk.formatted)
    parts.append("[END MEMORIES]")
    return "\n\n".join(parts)
