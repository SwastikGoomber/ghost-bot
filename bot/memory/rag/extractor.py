"""
RAG extractor — calls Gemini to extract structured memory chunks from ALL segments in one call.

The extractor is the cognitive core of the ingestion pipeline. Instead of making one LLM
call per conversation segment, it batches the entire ingestion run into a single call:

    segments (N) → one prompt → one generate_json() call → N ExtractionResults

This eliminates the per-segment API call overhead, respects rate limits, and lets the
model reason across the full temporal window for better arc tag consistency.

Model: gemini-2.5-pro (configured via config.yaml extractor role) — needed for the long
output window (up to 65K tokens) that a batch of dozens of segments requires.

Every LLM call uses JSON mode (generate_json) so the output is always parseable.
If parsing fails for individual entries, those segments are skipped and logged —
the run never crashes on a single bad segment.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from bot.utils.llm.registry import get_llm_client
from bot.utils.llm.gemini import GeminiClient
from bot.utils.exceptions import LLMError

from .models import BatchExtractionResult, ExtractionResult, MessageSegment

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path("prompts/rag_extractor.md")


def _load_prompt() -> str:
    """Load the extractor prompt template."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _build_taxonomy_context(existing_arc_tags: list[str]) -> str:
    """
    Build the taxonomy section injected into the extractor prompt.

    Includes the fixed classifications, namespace definitions, and the currently
    known arc tags so the LLM uses existing arcs rather than inventing new ones.
    """
    classifications = [
        "conversation", "lore", "event", "fact", "character_development",
        "relationship", "worldbuilding", "decisions", "mysteries", "arc_summary", "others",
    ]
    sentiments = ["light", "tense", "dramatic", "humorous", "emotional"]

    arc_tag_list = "\n".join(f"  - {t}" for t in sorted(existing_arc_tags)) or "  (none yet)"

    return f"""### Classifications
{chr(10).join(f"  - {c}" for c in classifications)}

### Sentiment values
{chr(10).join(f"  - {s}" for s in sentiments)}

### Tag namespaces
  - arc:         Story arcs (existing arcs listed below)
  - individual:  Specific people or characters
  - location:    Specific places
  - topic:       Recurring themes or subjects
  - lore:        Named bodies of lore

### Known arc tags (use these in `tags` field; propose new ones in `suggested_tags`)
{arc_tag_list}"""


def _build_segments_block(segments: list[MessageSegment]) -> str:
    """
    Render all segments as a single numbered block for the batch prompt.

    Format:
        [SEGMENT 0] 2025-10-13 10:00 → 2025-10-13 10:45
        [2025-10-13 10:00] UserA: message
        [2025-10-13 10:02] Ghost: reply
        ...

        [SEGMENT 1] ...
    """
    blocks: list[str] = []
    for i, seg in enumerate(segments):
        start = seg.start_time.strftime("%Y-%m-%d %H:%M")
        end = seg.end_time.strftime("%Y-%m-%d %H:%M")
        header = f"[SEGMENT {i}] {start} → {end}"
        body = seg.format_for_prompt()
        blocks.append(f"{header}\n{body}")
    return "\n\n".join(blocks)


async def extract_segments_batch(
    segments: list[MessageSegment],
    existing_arc_tags: list[str],
) -> list[Optional[ExtractionResult]]:
    """
    Run the extractor LLM on ALL segments in a single API call.

    Args:
        segments:          All conversation segments to process for this ingestion run.
        existing_arc_tags: All arc: tags currently in the taxonomy (for prompt context).

    Returns:
        A list of the same length as `segments`.
        Each element is either an ExtractionResult (worth storing) or None (not worth
        storing, or extraction failed for that segment).

    Raises:
        LLMError: If the LLM call itself fails entirely (network, auth, quota exhausted
                  with no fallback). Per-segment parse failures do NOT raise — they return None.
    """
    if not segments:
        return []

    client = get_llm_client("extractor")
    if not isinstance(client, GeminiClient):
        raise LLMError("The 'extractor' role must map to a GeminiClient.")

    prompt_template = _load_prompt()
    taxonomy_str = _build_taxonomy_context(existing_arc_tags)
    segments_str = _build_segments_block(segments)

    filled_prompt = (
        prompt_template
        .replace("{taxonomy}", taxonomy_str)
        .replace("{segments}", segments_str)
    )

    logger.info(
        "Extractor: sending batch of %d segments (%d total messages) to %s",
        len(segments),
        sum(len(s.messages) for s in segments),
        client.model,
    )

    messages = [{"role": "user", "content": filled_prompt}]

    try:
        raw_json = await client.generate_json(messages)
    except LLMError as exc:
        # Entire batch failed — raise so the caller can log and abort
        raise LLMError(f"Batch extractor LLM call failed: {exc}") from exc

    # ---------------------------------------------------------------------------
    # Parse the batch response
    # ---------------------------------------------------------------------------
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error(
            "Batch extractor returned non-JSON. Skipping all %d segments. Error: %s\nRaw (first 500 chars): %.500s",
            len(segments),
            exc,
            raw_json,
        )
        return [None] * len(segments)

    try:
        batch = BatchExtractionResult.model_validate(data)
    except ValidationError as exc:
        logger.error(
            "Batch extractor JSON failed top-level Pydantic validation. "
            "Skipping all %d segments. Error: %s",
            len(segments),
            exc,
        )
        return [None] * len(segments)

    # Build a lookup dict: segment_index → SegmentExtractionResult
    index_to_result = {entry.segment_index: entry for entry in batch.extractions}

    results: list[Optional[ExtractionResult]] = []
    stored_count = 0
    skipped_count = 0

    for i, segment in enumerate(segments):
        entry = index_to_result.get(i)

        if entry is None:
            # LLM omitted this index entirely — treat as not worth storing
            logger.debug(
                "Segment %d (starting %s) was omitted from batch response — treating as not worth storing.",
                i, segment.start_time.isoformat(),
            )
            results.append(None)
            skipped_count += 1
            continue

        if not entry.worth_storing:
            logger.debug(
                "Segment %d (starting %s) marked not worth storing.",
                i, segment.start_time.isoformat(),
            )
            results.append(None)
            skipped_count += 1
            continue

        # Cast SegmentExtractionResult → ExtractionResult (drop segment_index)
        try:
            result = ExtractionResult.model_validate(entry.model_dump(exclude={"segment_index"}))
        except ValidationError as exc:
            logger.error(
                "Segment %d (starting %s) failed per-entry validation — skipping. Error: %s",
                i, segment.start_time.isoformat(), exc,
            )
            results.append(None)
            skipped_count += 1
            continue

        results.append(result)
        stored_count += 1

    logger.info(
        "Extractor batch complete: %d segments → %d to store, %d skipped.",
        len(segments), stored_count, skipped_count,
    )
    return results


async def check_contradiction(
    new_fact_summary: str,
    new_fact_id: str,
    existing_facts: list,  # list[RAGDocument]
) -> tuple[bool, Optional[str]]:
    """
    Run the contradiction checker LLM against a new fact and existing facts.

    Returns:
        (contradiction_detected, contradicted_chunk_id)

    If no contradiction is found, returns (False, None).
    If parsing fails, returns (False, None) — we never block ingestion on a checker failure.
    """
    if not existing_facts:
        return False, None

    from .models import ContradictionCheckResult

    prompt_path = Path("prompts/rag_contradiction_checker.md")
    prompt_template = prompt_path.read_text(encoding="utf-8")

    existing_facts_str = "\n\n".join(
        f"[Chunk ID: {f.id}]\n{f.summary}" for f in existing_facts
    )

    filled_prompt = (
        prompt_template
        .replace("{new_fact}", f"[Chunk ID: {new_fact_id}]\n{new_fact_summary}")
        .replace("{existing_facts}", existing_facts_str)
    )

    client = get_llm_client("extractor")
    if not isinstance(client, GeminiClient):
        return False, None

    try:
        raw_json = await client.generate_json([{"role": "user", "content": filled_prompt}])
        data = json.loads(raw_json)
        result = ContradictionCheckResult.model_validate(data)
        return result.contradiction_detected, result.contradicted_chunk_id
    except Exception as exc:
        logger.warning("Contradiction checker failed (non-blocking): %s", exc)
        return False, None
