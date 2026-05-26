"""
RAGQueryPlanner — constructs a precise RetrievalQuery from a user message.

Uses Gemma 4 E4B (via Ollama) with a live taxonomy snapshot injected into
the prompt so it can reference actual arc tags, individual names, and doc
types that exist in the database.

The planner is the only place that translates natural-language intent into
the logic-gate filter clauses (AND/OR/NOT) that map to MongoDB operators.

Usage:
    planner = RAGQueryPlanner(taxonomy_snapshot)
    query = await planner.plan(message)
    chunks = await retrieve(query)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ..utils.config import get_config
from ..utils.exceptions import LLMError
from ..utils.llm import get_llm_client
from ..utils.llm.ollama import OllamaClient
from ..utils.models import (
    FilterClause,
    LogicGate,
    RetrievalQuery,
    TaxonomySnapshot,
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "rag_planner.md"
_PLANNER_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")


def _format_taxonomy(snapshot: TaxonomySnapshot) -> str:
    """Render the taxonomy snapshot into a compact human-readable block for injection."""
    lines = []

    if snapshot.known_individuals:
        lines.append(f"Known individuals: {', '.join(snapshot.known_individuals)}")
    if snapshot.known_locations:
        lines.append(f"Known locations: {', '.join(snapshot.known_locations)}")
    if snapshot.known_topics:
        lines.append(f"Known topics: {', '.join(snapshot.known_topics)}")
    if snapshot.arc_tags:
        tag_parts = [f"{tag} ({count} chunks)" for tag, count in snapshot.arc_tags.items()]
        lines.append(f"Arc tags: {', '.join(tag_parts)}")
    if snapshot.doc_type_counts:
        type_parts = [f"{dt} ({count})" for dt, count in snapshot.doc_type_counts.items()]
        lines.append(f"Doc types: {', '.join(type_parts)}")

    return "\n".join(lines) if lines else "(empty database — no chunks ingested yet)"


def _parse_filter_clause(raw: Optional[dict]) -> Optional[FilterClause]:
    """Parse a raw dict into a FilterClause, returning None if invalid/empty."""
    if not raw or not isinstance(raw, dict):
        return None
    values = raw.get("values", [])
    if not values or not isinstance(values, list):
        return None
    gate_str = raw.get("gate", "OR").upper()
    try:
        gate = LogicGate(gate_str)
    except ValueError:
        gate = LogicGate.OR
    return FilterClause(values=[str(v) for v in values], gate=gate)


class RAGQueryPlanner:
    """
    Translates a natural-language message into a RetrievalQuery.

    Instantiate with a TaxonomySnapshot (cached at startup, refreshed post-ingestion).
    The snapshot is injected into the prompt so the model can use real values.
    """

    def __init__(self, taxonomy: TaxonomySnapshot) -> None:
        self._taxonomy = taxonomy

    async def plan(
        self,
        message: str,
        recent_messages: Optional[list] = None,
        channel_context: Optional[list] = None,
        reply_context: Optional[object] = None,
    ) -> RetrievalQuery:
        """
        Generate a RetrievalQuery for the given message, using recent context if available.

        Falls back to a simple text-only query on any failure so the pipeline
        always gets *something* to pass to the retriever.

        Args:
            message: Raw user message text.
            recent_messages: Optional list of recent Message objects representing conversation history.
            channel_context: Optional list of ambient messages from the current channel.
            reply_context: Optional message object that is being replied to.

        Returns:
            RetrievalQuery with logic-gate filters and semantic query text.
        """
        cfg = get_config()
        client = get_llm_client("rag_planner")
        if client is None:
            logger.error("RAG planner client is not available — using fallback query.")
            return _fallback_query(message, cfg.rag.retrieval_top_k)

        # Build rich conversation history block
        history_lines = []
        
        # 1. Inject reply target if present
        if reply_context:
            try:
                history_lines.append(f"[Reply Target] {reply_context.username}: {reply_context.content}")
            except AttributeError:
                pass

        # 2. Inject ambient channel messages if present
        if channel_context:
            for msg in channel_context:
                try:
                    history_lines.append(f"{msg.username}: {msg.content}")
                except AttributeError:
                    pass
        # 3. Fallback to private user history if no channel context exists
        elif recent_messages:
            for msg in recent_messages:
                speaker = "Ghost" if msg.from_bot else "User"
                history_lines.append(f"{speaker}: {msg.content}")

        history_block = ""
        if history_lines:
            # Cap to last 12 messages (6 turns) to avoid bloating prompt context
            history_lines = history_lines[-12:]
            history_block = "## Recent Conversation Context:\n" + "\n".join(history_lines) + "\n\n"

        taxonomy_text = _format_taxonomy(self._taxonomy)
        system_prompt = _PLANNER_PROMPT_TEMPLATE.replace("{taxonomy_snapshot}", taxonomy_text)

        user_content = ""
        if history_block:
            user_content += f"{history_block}\n"
        user_content += f"## Message to process:\n{message}"

        try:
            raw = await client.generate_json(
                messages=[{"role": "user", "content": user_content}],
                system_prompt=system_prompt,
            )
            
            cleaned_raw = raw.strip()
            import re
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_raw, re.DOTALL)
            if json_match:
                cleaned_raw = json_match.group(1).strip()
            elif not cleaned_raw.startswith("{") and "{" in cleaned_raw:
                start = cleaned_raw.find("{")
                end = cleaned_raw.rfind("}")
                if start != -1 and end != -1:
                    cleaned_raw = cleaned_raw[start:end+1]

            if not cleaned_raw:
                logger.warning("RAGQueryPlanner received empty response from Ollama — using fallback query.")
                return _fallback_query(message, cfg.rag.retrieval_top_k)

            data = json.loads(cleaned_raw)

            query = RetrievalQuery(
                query_text=str(data.get("query_text", message)),
                individual_filter=_parse_filter_clause(data.get("individual_filter")),
                arc_tag_filter=_parse_filter_clause(data.get("arc_tag_filter")),
                doc_type_filter=_parse_filter_clause(data.get("doc_type_filter")),
                exclude_individuals=[
                    str(v) for v in data.get("exclude_individuals", [])
                    if isinstance(v, str)
                ],
                min_significance=int(data.get("min_significance", 1)),
                time_range_start=data.get("time_range_start") or None,
                time_range_end=data.get("time_range_end") or None,
                top_k=int(data.get("top_k", cfg.rag.retrieval_top_k)),
            )
            logger.debug(
                "RAG planner built query: text=%r, ind=%s, arc=%s, type=%s",
                query.query_text[:60],
                query.individual_filter,
                query.arc_tag_filter,
                query.doc_type_filter,
            )
            return query

        except json.JSONDecodeError as exc:
            logger.warning("RAGQueryPlanner JSON parse failed. Raw output: %r. Error: %s", raw, exc)
            return _fallback_query(message, cfg.rag.retrieval_top_k)
        except (LLMError, ValueError) as exc:
            logger.warning("RAGQueryPlanner failed (%s) — using fallback query.", exc)
            return _fallback_query(message, cfg.rag.retrieval_top_k)


def _fallback_query(message: str, top_k: int) -> RetrievalQuery:
    """Minimal fallback: raw message text as the semantic query, no filters."""
    return RetrievalQuery(query_text=message, top_k=top_k)
