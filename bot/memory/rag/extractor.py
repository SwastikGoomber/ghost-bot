"""
RAG extractor — calls Gemini to extract structured memory chunks from message segments.

The extractor is the cognitive core of the ingestion pipeline. It takes a raw
conversation segment and produces a fully structured ExtractionResult (or indicates
the segment isn't worth storing).

Every LLM call uses JSON mode (generate_json) so the output is always parseable.
If parsing fails, the segment is skipped and the failure is logged — never crashes
the ingestion run.

The extractor also builds the taxonomy context string that is injected into the
prompt so the LLM only proposes tags that fit existing namespaces.
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

from .models import ExtractionResult, MessageSegment

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path("prompts/rag_extractor.md")


def _load_prompt() -> str:
    """Load the extractor prompt template. Cached implicitly since it's called per-run."""
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


async def extract_segment(
    segment: MessageSegment,
    existing_arc_tags: list[str],
    recent_chunk_ids: Optional[list[str]] = None,
) -> Optional[ExtractionResult]:
    """
    Run the extractor LLM on a single MessageSegment.

    Args:
        segment:           The conversation segment to extract.
        existing_arc_tags: All arc: tags currently in the taxonomy (for prompt context).
        recent_chunk_ids:  IDs of the most recently stored chunks (passed as [RELATED_CHUNKS]
                           context so the LLM can identify continuations).

    Returns:
        ExtractionResult if the LLM produced valid output.
        None if the segment is not worth storing OR if extraction failed (both are logged).

    Raises:
        LLMError: Only on severe, unexpected LLM failures — normal extraction errors
                  return None rather than raising.
    """
    client = get_llm_client("extractor")
    if not isinstance(client, GeminiClient):
        raise LLMError("The 'extractor' role must map to a GeminiClient.")

    prompt_template = _load_prompt()
    taxonomy_str = _build_taxonomy_context(existing_arc_tags)
    segment_str = segment.format_for_prompt()
    related_str = "\n".join(recent_chunk_ids or []) or "(none)"

    filled_prompt = (
        prompt_template
        .replace("{taxonomy}", taxonomy_str)
        .replace("{segment}", segment_str)
        .replace("{related_chunks}", related_str)
    )

    messages = [{"role": "user", "content": filled_prompt}]

    try:
        raw_json = await client.generate_json(messages)
    except LLMError as exc:
        logger.error(
            "Extractor LLM call failed for segment starting %s: %s",
            segment.start_time.isoformat(),
            exc,
        )
        return None

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error(
            "Extractor returned non-JSON for segment starting %s: %s\nRaw: %.200s",
            segment.start_time.isoformat(),
            exc,
            raw_json,
        )
        return None

    try:
        result = ExtractionResult.model_validate(data)
    except ValidationError as exc:
        logger.error(
            "Extractor JSON failed Pydantic validation for segment starting %s: %s",
            segment.start_time.isoformat(),
            exc,
        )
        return None

    if not result.worth_storing:
        logger.debug(
            "Extractor marked segment starting %s as not worth storing.",
            segment.start_time.isoformat(),
        )
        return None

    return result


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
