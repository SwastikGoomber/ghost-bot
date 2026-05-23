"""
RAG document store — MongoDB read/write and Atlas Vector Search.

All persistence for the RAG pipeline goes through this module.
Callers never touch MongoDB directly — they call functions here.

Collections used:
    rag_documents        — main chunk store
    rag_suggested_tags   — tag proposals awaiting human review (name configurable)

Index setup:
    Regular indexes are created by create_indexes() (call once at startup if needed).
    The vector search index must be created manually in Atlas:
        - Index name: rag_vector_index
        - Field: embedding
        - Dimensions: 1024  (nomic-embed-large)
        - Similarity: cosine

Atlas Vector Search on M0 free tier:
    As of 2025, Atlas Vector Search is available on M0 free tier.
    Create the index via Atlas UI > Database > Search Indexes > Create Search Index > Atlas Vector Search.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from bot.memory.db import get_db
from bot.utils.config import get_config

from .models import (
    RAGDocument,
    ArcTagStats,
    ChunkStatus,
    DocType,
    IngestionReport,
)

logger = logging.getLogger(__name__)

COLLECTION = "rag_documents"


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

async def create_indexes() -> None:
    """
    Create regular MongoDB indexes for fast metadata queries.

    Call once at startup (idempotent — MongoDB ignores duplicates).
    The vector search index (rag_vector_index) must be created separately in Atlas UI.
    """
    db = get_db()
    coll = db[COLLECTION]
    await coll.create_index("status")
    await coll.create_index("doc_type")
    await coll.create_index("individuals")
    await coll.create_index("tags")
    await coll.create_index("source_message_ids")
    await coll.create_index("significance")
    await coll.create_index("ingested_at")
    await coll.create_index([("status", 1), ("doc_type", 1), ("significance", 1)])
    logger.info("RAG collection indexes created/verified.")


# ---------------------------------------------------------------------------
# Deduplication check
# ---------------------------------------------------------------------------

async def find_existing_by_message_ids(message_ids: list[str]) -> bool:
    """
    Return True if any of the given Discord message IDs have already been ingested.

    Used to skip segments that were already processed in a previous run.
    """
    db = get_db()
    doc = await db[COLLECTION].find_one(
        {"source_message_ids": {"$in": message_ids}},
        {"_id": 1},
    )
    return doc is not None


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

async def insert_document(doc: RAGDocument) -> str:
    """Persist a new RAGDocument. Returns the chunk ID."""
    db = get_db()
    data = doc.model_dump(mode="json")
    data["_id"] = doc.id  # Use our UUID as the MongoDB _id
    await db[COLLECTION].insert_one(data)
    logger.debug("Inserted RAG chunk %s (type=%s, significance=%d)", doc.id, doc.doc_type, doc.significance)
    return doc.id


async def update_status(chunk_id: str, status: ChunkStatus) -> None:
    """Update the lifecycle status of a chunk."""
    db = get_db()
    await db[COLLECTION].update_one(
        {"_id": chunk_id},
        {"$set": {"status": status.value}},
    )


async def mark_contradiction_flagged(chunk_id: str) -> None:
    """Flag a chunk as having a potential contradiction with existing data."""
    db = get_db()
    await db[COLLECTION].update_one(
        {"_id": chunk_id},
        {"$set": {"potential_contradiction": True}},
    )


async def mark_summarized(chunk_ids: list[str]) -> None:
    """Mark chunks as covered by an arc_summary — they remain but are deprioritised."""
    if not chunk_ids:
        return
    db = get_db()
    await db[COLLECTION].update_many(
        {"_id": {"$in": chunk_ids}},
        {"$set": {"is_summarized": True}},
    )


async def supersede_chunk(old_chunk_id: str, new_chunk_id: str) -> None:
    """
    Mark old_chunk as superseded by new_chunk.

    Called when a new fact contradicts and replaces an older one.
    The old chunk is not deleted — it remains for historical queries.
    """
    db = get_db()
    await db[COLLECTION].update_one(
        {"_id": old_chunk_id},
        {"$set": {"status": ChunkStatus.SUPERSEDED.value}},
    )
    logger.info("Chunk %s superseded by %s", old_chunk_id, new_chunk_id)


# ---------------------------------------------------------------------------
# Read — fact contradiction check
# ---------------------------------------------------------------------------

async def find_active_facts_for_individuals(individuals: list[str]) -> list[RAGDocument]:
    """
    Return active fact chunks that involve any of the given individuals.

    Used during ingestion to find potential contradictions with a new fact chunk.
    """
    if not individuals:
        return []
    db = get_db()
    cursor = db[COLLECTION].find({
        "doc_type": DocType.FACT.value,
        "status": ChunkStatus.ACTIVE.value,
        "individuals": {"$in": individuals},
    })
    docs = []
    async for raw in cursor:
        raw["id"] = raw.pop("_id")
        try:
            docs.append(RAGDocument.model_validate(raw))
        except Exception as exc:
            logger.warning("Failed to parse RAG doc %s: %s", raw.get("id"), exc)
    return docs


# ---------------------------------------------------------------------------
# Read — arc summary agent
# ---------------------------------------------------------------------------

async def get_arc_tag_stats(updated_arc_tags: list[str]) -> list[ArcTagStats]:
    """
    For each arc tag, compute the stats needed to decide whether to trigger summarisation.

    updated_arc_tags: arc tags that received new chunks in the current ingestion run.
    """
    if not updated_arc_tags:
        return []

    db = get_db()
    stats = []

    for arc_tag in updated_arc_tags:
        pipeline = [
            {"$match": {
                "tags": arc_tag,
                "status": ChunkStatus.ACTIVE.value,
                "is_summarized": False,
            }},
            {"$group": {
                "_id": None,
                "count": {"$sum": 1},
                "total_summary_chars": {"$sum": {"$strLenCP": "$summary"}},
                "last_ingested_at": {"$max": "$ingested_at"},
            }},
        ]
        result = await db[COLLECTION].aggregate(pipeline).to_list(length=1)
        if not result:
            continue

        row = result[0]
        # Rough token estimate: 1 token ≈ 4 chars
        estimated_tokens = row["total_summary_chars"] // 4

        has_summary = await db[COLLECTION].count_documents({
            "doc_type": DocType.ARC_SUMMARY.value,
            "tags": arc_tag,
            "status": ChunkStatus.ACTIVE.value,
        }) > 0

        last_ingested = row.get("last_ingested_at")
        if isinstance(last_ingested, str):
            last_ingested = datetime.fromisoformat(last_ingested)

        stats.append(ArcTagStats(
            arc_tag=arc_tag,
            active_chunk_count=row["count"],
            estimated_total_tokens=estimated_tokens,
            last_ingested_at=last_ingested,
            has_existing_summary=has_summary,
        ))

    return stats


async def get_active_chunks_for_arc(arc_tag: str) -> list[RAGDocument]:
    """
    Return all active, unsummarised chunks for a given arc tag, sorted by event_date.

    Used by the arc summary agent to feed chunks into the summariser LLM.
    """
    db = get_db()
    cursor = db[COLLECTION].find(
        {
            "tags": arc_tag,
            "status": ChunkStatus.ACTIVE.value,
            "is_summarized": False,
            "doc_type": {"$ne": DocType.ARC_SUMMARY.value},
        },
        sort=[("event_date", 1), ("ingested_at", 1)],
    )
    docs = []
    async for raw in cursor:
        raw["id"] = raw.pop("_id")
        try:
            docs.append(RAGDocument.model_validate(raw))
        except Exception as exc:
            logger.warning("Failed to parse RAG doc for arc %s: %s", arc_tag, exc)
    return docs


# ---------------------------------------------------------------------------
# Read — taxonomy helpers
# ---------------------------------------------------------------------------

async def get_distinct_arc_tags() -> list[str]:
    """Return all distinct arc: tags currently in the collection (active chunks only)."""
    db = get_db()
    raw_tags = await db[COLLECTION].distinct("tags", {"status": ChunkStatus.ACTIVE.value})
    return [t for t in raw_tags if isinstance(t, str) and t.startswith("arc:")]


# ---------------------------------------------------------------------------
# Suggested tag review queue
# ---------------------------------------------------------------------------

async def store_suggested_tags(
    chunk_id: str,
    suggested_tags: list[str],
    justifications: dict[str, str],
) -> None:
    """
    Write new tag suggestions to the review queue collection.

    Each suggestion is stored as a separate document for easy querying and filtering.
    The review queue is queryable via a script when the human wants to do a weekly review.
    """
    if not suggested_tags:
        return
    cfg = get_config()
    db = get_db()
    coll = db[cfg.rag.suggested_tag_collection]

    docs = []
    for tag in suggested_tags:
        docs.append({
            "_id": str(uuid.uuid4()),
            "tag": tag,
            "justification": justifications.get(tag, ""),
            "source_chunk_id": chunk_id,
            "suggested_at": datetime.utcnow().isoformat(),
            "reviewed": False,
        })

    if docs:
        await coll.insert_many(docs)
        logger.debug("Stored %d suggested tag(s) for review.", len(docs))


# ---------------------------------------------------------------------------
# Vector search retrieval
# ---------------------------------------------------------------------------

async def vector_search(
    query_embedding: list[float],
    doc_types: list[str],
    tags_must_include: list[str],
    individuals_must_include: list[str],
    min_significance: int,
    num_candidates: int = 100,
    limit: int = 20,
) -> list[dict]:
    """
    Run Atlas Vector Search with metadata pre-filtering.

    Returns raw MongoDB documents (dicts) sorted by vector similarity.
    The caller (retriever) applies significance weighting and final top-K cutoff.

    Args:
        query_embedding:          Vector embedding of the retrieval query text.
        doc_types:                If non-empty, restrict to these doc_types.
        tags_must_include:        If non-empty, all of these tags must be present.
        individuals_must_include: If non-empty, all of these individuals must be present.
        min_significance:         Minimum significance score.
        num_candidates:           Candidates considered by vector search before filtering.
        limit:                    Maximum documents returned by vector search.

    Returns:
        List of raw document dicts, each with a `vector_score` field added.
    """
    db = get_db()

    # Build the metadata filter — always exclude non-active and summarized chunks
    # (is_summarized chunks exist but are deprioritised; the arc_summary covers them)
    mongo_filter: dict = {
        "status": ChunkStatus.ACTIVE.value,
        "significance": {"$gte": min_significance},
    }

    if doc_types:
        # Prefer arc_summary chunks — if searching by doc_type and arc_summary isn't listed,
        # add it so the arc-level summary is always eligible alongside individual chunks.
        # The retriever handles deduplication to avoid surfacing both.
        search_types = list(doc_types)
        if DocType.ARC_SUMMARY.value not in search_types:
            search_types.append(DocType.ARC_SUMMARY.value)
        mongo_filter["doc_type"] = {"$in": search_types}

    if tags_must_include:
        mongo_filter["tags"] = {"$all": tags_must_include}

    if individuals_must_include:
        mongo_filter["individuals"] = {"$all": individuals_must_include}

    pipeline = [
        {
            "$vectorSearch": {
                "index": "rag_vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": num_candidates,
                "limit": limit,
                "filter": mongo_filter,
            }
        },
        {
            "$addFields": {
                "vector_score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = []
    async for doc in db[COLLECTION].aggregate(pipeline):
        results.append(doc)

    return results


async def metadata_only_search(
    doc_types: list[str],
    tags_must_include: list[str],
    individuals_must_include: list[str],
    min_significance: int,
    limit: int = 30,
) -> list[dict]:
    """
    Metadata-only fallback when embeddings are not available or the query has no text.

    Returns results sorted by significance descending, then ingested_at descending.
    """
    db = get_db()

    mongo_filter: dict = {
        "status": ChunkStatus.ACTIVE.value,
        "significance": {"$gte": min_significance},
    }

    if doc_types:
        search_types = list(doc_types)
        if DocType.ARC_SUMMARY.value not in search_types:
            search_types.append(DocType.ARC_SUMMARY.value)
        mongo_filter["doc_type"] = {"$in": search_types}

    if tags_must_include:
        mongo_filter["tags"] = {"$all": tags_must_include}

    if individuals_must_include:
        mongo_filter["individuals"] = {"$all": individuals_must_include}

    cursor = db[COLLECTION].find(
        mongo_filter,
        sort=[("significance", -1), ("ingested_at", -1)],
        limit=limit,
    )
    results = []
    async for doc in cursor:
        doc["vector_score"] = 0.0  # No vector score in fallback path
        results.append(doc)
    return results
