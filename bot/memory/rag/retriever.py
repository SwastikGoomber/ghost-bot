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

import difflib
import logging
from typing import Optional

from bot.utils.config import get_config
from bot.utils.models import FilterClause, LogicGate, RetrievalQuery, RetrievedChunk, TaxonomySnapshot
from bot.utils.exceptions import LLMError

from .embedder import embed_text
from .models import DocType, RAGDocument
from .store import vector_search, metadata_only_search

logger = logging.getLogger(__name__)


def _get_name_candidates(name: str, known_names: list[str], cutoff: float = 0.6) -> list[str]:
    """
    Return ALL canonical names from the taxonomy that fuzzy-match the given name.

    Comparison is case-insensitive so 'Ghost' matches both 'Ghost' and 'GH0ST'
    (difflib ratio ~0.8 for 'ghost' vs 'gh0st', and 1.0 for exact lowercase match).

    Using n=10 so we don't miss aliases — the result is used as an $in list,
    so false positives are harmless while false negatives break retrieval.

    Returns the original name (unchanged) as a fallback if no match is found.
    """
    if not known_names:
        return [name]
    name_lower = name.lower()
    known_lower = [n.lower() for n in known_names]
    matches = difflib.get_close_matches(name_lower, known_lower, n=10, cutoff=cutoff)
    if not matches:
        logger.debug("[candidates] '%s' — no fuzzy match found, using as-is", name)
        return [name]
    candidates = [known_names[known_lower.index(m)] for m in matches]
    if len(candidates) > 1 or candidates[0] != name:
        logger.debug("[candidates] '%s' → %s (fuzzy candidates)", name, candidates)
    return candidates


async def retrieve(
    query: RetrievalQuery,
    taxonomy: Optional[TaxonomySnapshot] = None,
) -> list[RetrievedChunk]:
    """
    Execute a hybrid retrieval query and return ranked, formatted results.

    Args:
        query:    Structured retrieval query (from the RAG planner or handler).
        taxonomy: Optional taxonomy snapshot — used to expand individual names
                  to all fuzzy-matching canonical forms so 'Ghost' matches both
                  'Ghost' and 'GH0ST' stored in the DB.

    Returns:
        Up to query.top_k RetrievedChunk objects, sorted by final score descending.
        Returns an empty list if no results are found or if retrieval fails.
    """
    cfg = get_config()
    top_k = query.top_k or cfg.rag.retrieval_top_k

    known_individuals = taxonomy.known_individuals if taxonomy else []

    # Build filters:
    #   atlas_filter  → passed to $vectorSearch.filter (only indexed fields, currently {})
    #   post_filter   → applied as $match after vector search
    atlas_filter, post_filter = _build_mongo_filter(query, known_individuals)

    if cfg.rag.post_filter_disabled:
        logger.debug("[retrieve] post_filter_disabled=true — skipping $match post-filter")
        post_filter = {}

    # Embed the query text
    try:
        query_embedding = await embed_text(query.query_text)
    except LLMError as exc:
        logger.error("Retrieval embedding failed: %s. Falling back to metadata-only search.", exc)
        query_embedding = None

    # Fetch candidates
    if query_embedding is not None:
        raw_docs = await vector_search(
            query_embedding=query_embedding,
            atlas_filter=atlas_filter,
            post_filter=post_filter,
            num_candidates=min(top_k * 20, 200),
            limit=top_k * 4,
        )
    else:
        raw_docs = await metadata_only_search(
            extra_filter={**atlas_filter, **post_filter} if atlas_filter else post_filter,
            limit=top_k * 4,
        )

    if not raw_docs:
        logger.debug(
            "Retrieval returned 0 candidates for query: %.80s | post_filter=%s",
            query.query_text, post_filter,
        )
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

    logger.debug("Retrieval returned %d results for query: %.80s", len(results), query.query_text)
    for i, chunk in enumerate(results):
        logger.debug(
            "  [%d] id=%.12s type=%-12s score=%.4f sig=%d individuals=%s",
            i + 1,
            chunk.chunk_id,
            chunk.doc_type,
            chunk.score,
            chunk.significance,
            chunk.individuals,
        )
        logger.debug("  [%d] full text:\n%s", i + 1, chunk.formatted)
    return results


# ---------------------------------------------------------------------------
# Filter translation: FilterClause → MongoDB
# ---------------------------------------------------------------------------

def _build_mongo_filter(
    query: RetrievalQuery,
    known_individuals: list[str],
) -> tuple[dict, dict]:
    """
    Translate RetrievalQuery into (atlas_filter, post_filter).

    For individual name filtering, all fuzzy-matching canonical names are
    collected via _get_name_candidates so that 'Ghost' matches both 'Ghost'
    and 'GH0ST' in the DB.

    AND gate: $and[ {individuals: {$in: candidates_A}}, {individuals: {$in: candidates_B}} ]
    OR  gate: {individuals: {$in: all_candidates_combined}}
    NOT gate: {individuals: {$nin: all_candidates_combined}}

    atlas_filter: always {} until Atlas index has filter fields declared.
    post_filter:  $match stage after $vectorSearch.
    """
    atlas_filter: dict = {}

    post_and: list[dict] = [
        {"status": {"$eq": "active"}},
        {"significance": {"$gte": query.min_significance}},
    ]

    # --- individuals ---
    if query.individual_filter:
        clause = query.individual_filter
        if clause.gate == LogicGate.AND:
            # Each required individual gets its own $in with all fuzzy-matched aliases.
            # This correctly handles 'Ghost' → ['Ghost', 'GH0ST'] both in the same doc.
            for name in clause.values:
                candidates = _get_name_candidates(name, known_individuals)
                post_and.append({"individuals": {"$in": candidates}})
        elif clause.gate == LogicGate.NOT:
            all_candidates = []
            for name in clause.values:
                all_candidates.extend(_get_name_candidates(name, known_individuals))
            post_and.append({"individuals": {"$nin": list(set(all_candidates))}})
        else:  # OR
            all_candidates = []
            for name in clause.values:
                all_candidates.extend(_get_name_candidates(name, known_individuals))
            post_and.append({"individuals": {"$in": list(set(all_candidates))}})

    if query.exclude_individuals:
        all_excluded = []
        for name in query.exclude_individuals:
            all_excluded.extend(_get_name_candidates(name, known_individuals))
        post_and.append({"individuals": {"$nin": list(set(all_excluded))}})

    # --- arc tags ---
    if query.arc_tag_filter:
        clause = query.arc_tag_filter
        if clause.gate == LogicGate.AND:
            post_and.append({"tags": {"$all": clause.values}})
        elif clause.gate == LogicGate.NOT:
            post_and.append({"tags": {"$nin": clause.values}})
        else:  # OR
            post_and.append({"tags": {"$in": clause.values}})

    # --- doc types ---
    if query.doc_type_filter:
        clause = query.doc_type_filter
        if clause.gate == LogicGate.NOT:
            post_and.append({"doc_type": {"$nin": clause.values}})
        else:
            types_with_arc = list(set(clause.values) | {"arc_summary"})
            post_and.append({"doc_type": {"$in": types_with_arc}})

    # --- time range ---
    if query.time_range_start:
        post_and.append({"event_date": {"$gte": query.time_range_start}})
    if query.time_range_end:
        post_and.append({"event_date": {"$lte": query.time_range_end}})

    post_filter = {"$and": post_and} if len(post_and) > 1 else post_and[0]
    return atlas_filter, post_filter
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

    parts = [
        "[GHOST'S MEMORIES — real events and conversations you have lived through]\n"
        "Use these as follows:\n"
        "• If the current message is directly asking you to recall a specific event or conversation: "
        "draw on the relevant memory with genuine detail — names, what was said, how it felt. "
        "Don't just paraphrase vaguely.\n"
        "• If the memory is only tangentially related: let it quietly inform your response and "
        "attitude without forcing a direct reference. Stay conversational.\n"
        "• If none of these memories are relevant to what's being asked: ignore them entirely. "
        "Never shoehorn a memory into an unrelated conversation."
    ]
    for chunk in chunks:
        parts.append(chunk.formatted)
    parts.append("[END MEMORIES]")
    return "\n\n".join(parts)
