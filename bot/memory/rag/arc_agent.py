"""
Arc summary agent — generates cohesive narrative summaries for concluded or large arcs.

Triggered by ingestion.py after each daily run when either:
  1. The total token estimate for an arc's chunks exceeds arc_summary_token_threshold
  2. The arc hasn't received new chunks in arc_closure_gap_days days

What this module does:
  1. Pulls all active, unsummarised chunks for the arc, sorted by event_date
  2. Calls the arc_summarizer Gemini client with the arc summarizer prompt
  3. Stores the result as a new arc_summary chunk (high significance, same tags)
  4. Marks all source chunks with is_summarized=True (they remain, but deprioritised)

Arc summaries are first-class RAGDocument chunks — retrieved the same way as any other chunk.
They represent the "chapter summary" level on top of the raw "paragraph" level.

Embeddings are 768-dimensional vectors from nomic-embed-text.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from bot.utils.llm.registry import get_llm_client
from bot.utils.llm.gemini import GeminiClient
from bot.utils.exceptions import LLMError

from .embedder import embed_text
from .models import (
    ChunkStatus,
    DocType,
    RAGDocument,
    Sentiment,
)
from .store import (
    get_active_chunks_for_arc,
    insert_document,
    mark_summarized,
)

logger = logging.getLogger(__name__)

_ARC_SUMMARIZER_PROMPT_PATH = Path("prompts/rag_arc_summarizer.md")


async def generate_arc_summary(arc_tag: str) -> Optional[str]:
    """
    Generate and store an arc_summary chunk for the given arc tag.

    Args:
        arc_tag: The arc: tag (e.g. "arc:choccy-milk-heist-v2").

    Returns:
        The chunk ID of the newly created arc_summary, or None if generation failed.

    Raises:
        LLMError: If the arc_summarizer LLM call fails or Ollama embedding fails.
    """
    chunks = await get_active_chunks_for_arc(arc_tag)
    if not chunks:
        logger.warning("Arc summary triggered for %s but no active chunks found.", arc_tag)
        return None

    logger.info(
        "Generating arc summary for %s from %d source chunks.",
        arc_tag,
        len(chunks),
    )

    # Build the chunks context string for the prompt
    chunks_str = _format_chunks_for_prompt(chunks)

    prompt_template = _ARC_SUMMARIZER_PROMPT_PATH.read_text(encoding="utf-8")
    filled_prompt = (
        prompt_template
        .replace("{arc_tag}", arc_tag)
        .replace("{chunks}", chunks_str)
    )

    client = get_llm_client("arc_summarizer")
    if not isinstance(client, GeminiClient):
        raise LLMError("The 'arc_summarizer' role must map to a GeminiClient.")

    try:
        raw_json = await client.generate_json([{"role": "user", "content": filled_prompt}])
        data = json.loads(raw_json)
    except (LLMError, json.JSONDecodeError) as exc:
        raise LLMError(f"Arc summarizer LLM failed for {arc_tag}: {exc}") from exc

    summary_text = data.get("summary", "").strip()
    key_quotes = data.get("key_quotes", [])

    if not summary_text:
        raise LLMError(f"Arc summarizer returned empty summary for {arc_tag}.")

    # Collect all tags from source chunks (union) to inherit on the summary chunk
    all_tags: set[str] = set()
    all_individuals: set[str] = set()
    event_dates = []

    for chunk in chunks:
        all_tags.update(chunk.tags)
        all_individuals.update(chunk.individuals)
        if chunk.event_date:
            event_dates.append(chunk.event_date)

    # Date range for the arc summary: use earliest event date as the anchor
    arc_event_date = min(event_dates) if event_dates else None

    # Significance for arc summaries is always 4 (important, shapes retrieval)
    # unless the source chunks include significance-5 chunks (world-altering arc → 5)
    max_source_significance = max((c.significance for c in chunks), default=3)
    summary_significance = 5 if max_source_significance >= 5 else 4

    chunk_id = str(uuid.uuid4())
    arc_doc = RAGDocument(
        id=chunk_id,
        doc_type=DocType.ARC_SUMMARY,
        summary=summary_text,
        key_quotes=key_quotes,
        tags=list(all_tags),
        individuals=list(all_individuals),
        significance=summary_significance,
        sentiment=Sentiment.DRAMATIC,  # Arc summaries default to dramatic; acceptable approximation
        event_date=arc_event_date,
        source_channel_id=chunks[0].source_channel_id if chunks else "",
        source_message_ids=[],  # Arc summaries synthesise many sources; no single message IDs
    )

    # Embed the arc summary
    arc_doc.embedding = await embed_text(arc_doc.embedding_text())

    # Store the arc_summary chunk
    await insert_document(arc_doc)
    logger.info("Stored arc summary %s for %s (significance=%d)", chunk_id, arc_tag, summary_significance)

    # Mark all source chunks as summarized
    source_ids = [c.id for c in chunks]
    await mark_summarized(source_ids)
    logger.info("Marked %d source chunks as is_summarized=True for %s.", len(source_ids), arc_tag)

    return chunk_id


def _format_chunks_for_prompt(chunks: list[RAGDocument]) -> str:
    """
    Format source chunks into a readable string for the arc summarizer prompt.

    Includes doc_type, event_date, significance, individuals, and summary for each chunk.
    Key quotes are included verbatim.
    """
    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = f"[Chunk {i} | {chunk.doc_type} | sig:{chunk.significance} | {chunk.event_date or chunk.ingested_at.strftime('%Y-%m-%d')}]"
        people = ", ".join(chunk.individuals) if chunk.individuals else "unknown"
        body = f"Individuals: {people}\n{chunk.summary}"
        if chunk.key_quotes:
            quotes_str = "\n".join(f'  "{q}"' for q in chunk.key_quotes)
            body += f"\nKey quotes:\n{quotes_str}"
        parts.append(f"{header}\n{body}")
    return "\n\n".join(parts)
