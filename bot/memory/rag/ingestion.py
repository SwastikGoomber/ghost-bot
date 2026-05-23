"""
RAG ingestion — fetch Discord messages, segment them, and drive the extraction pipeline.

Ingestion flow (per the architecture plan):
    1. Fetch messages from enabled channels for the lookback window
    2. Filter out bots and very short messages
    3. Group messages into conversation segments (gap > conversation_gap_minutes = new segment)
    4. Deduplicate: skip segments whose message IDs were already ingested
    5. Batch extract ALL remaining segments in ONE LLM call (extract_segments_batch)
    6. For each result: embed → (fact: contradiction check) → store → queue suggested tags
    7. Post-ingestion: check arc tags for summary triggers

The Discord client reference is passed in from the job runner (via GhostDiscordBot).
This module never imports from bot.platforms — the platform layer passes itself down.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord

from bot.utils.config import get_config
from bot.utils.exceptions import LLMError

from .embedder import embed_text
from .extractor import extract_segments_batch, check_contradiction
from .models import (
    DocType,
    ExtractionResult,
    IngestionReport,
    MessageSegment,
    RAGDocument,
    RawMessage,
)
from .store import (
    find_existing_by_message_ids,
    get_distinct_arc_tags,
    find_active_facts_for_individuals,
    insert_document,
    mark_contradiction_flagged,
    store_suggested_tags,
    supersede_chunk,
    get_arc_tag_stats,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Top-level ingestion entry point
# ---------------------------------------------------------------------------

async def run_ingestion(discord_client: discord.Client) -> IngestionReport:
    """
    Execute a full ingestion run for all enabled channels.

    Called by the daily scheduler job (bot/jobs/rag_job.py).

    Args:
        discord_client: The live GhostDiscordBot instance (a discord.Client subclass).
                        Used to fetch channel message history.

    Returns:
        IngestionReport summarising what was processed and stored.
    """
    cfg = get_config()
    rag_cfg = cfg.rag
    report = IngestionReport()

    if not rag_cfg.enabled:
        logger.info("RAG ingestion is disabled (rag.enabled=false in config.yaml). Skipping.")
        return report

    if not rag_cfg.enabled_channel_ids:
        logger.warning("RAG is enabled but no channel IDs are configured. Nothing to ingest.")
        return report

    # Fetch the current arc taxonomy once — shared across all channel processing
    existing_arc_tags = await get_distinct_arc_tags()
    logger.info(
        "Starting RAG ingestion. Channels: %d, known arc tags: %d",
        len(rag_cfg.enabled_channel_ids),
        len(existing_arc_tags),
    )

    newly_used_arc_tags: set[str] = set()

    for channel_id in rag_cfg.enabled_channel_ids:
        channel = discord_client.get_channel(channel_id)
        if channel is None:
            logger.warning("Channel %d not found or not accessible. Skipping.", channel_id)
            continue
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            logger.warning("Channel %d is not a text channel. Skipping.", channel_id)
            continue

        report.channels_processed += 1
        arc_tags_from_channel = await _process_channel(
            channel=channel,
            lookback_hours=rag_cfg.extraction_lookback_hours,
            gap_minutes=rag_cfg.conversation_gap_minutes,
            min_words=rag_cfg.min_message_length_words,
            existing_arc_tags=existing_arc_tags,
            report=report,
        )
        newly_used_arc_tags.update(arc_tags_from_channel)
        # Refresh arc tag list for subsequent channels
        existing_arc_tags = await get_distinct_arc_tags()

    # Post-ingestion: check arc tags that received new chunks for summary triggers
    if newly_used_arc_tags:
        arc_stats = await get_arc_tag_stats(list(newly_used_arc_tags))
        triggered = await _check_arc_summary_triggers(arc_stats)
        report.arc_summaries_triggered.extend(triggered)

    logger.info(
        "Ingestion complete: %d chunks stored, %d contradictions flagged, %d arc summaries triggered.",
        report.chunks_stored,
        report.contradictions_flagged,
        len(report.arc_summaries_triggered),
    )
    return report


# ---------------------------------------------------------------------------
# Per-channel processing
# ---------------------------------------------------------------------------

async def _process_channel(
    channel: discord.TextChannel,
    lookback_hours: int,
    gap_minutes: int,
    min_words: int,
    existing_arc_tags: list[str],
    report: IngestionReport,
) -> list[str]:
    """
    Fetch, segment, dedup, batch-extract, and store from a single channel.

    Returns the list of arc tags used in chunks stored from this channel
    (for post-ingestion arc summary trigger checking).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    raw_messages = await _fetch_messages(channel, cutoff, min_words)

    if not raw_messages:
        logger.debug("No qualifying messages in channel %d for the lookback window.", channel.id)
        return []

    segments = _segment_messages(raw_messages, gap_minutes, str(channel.id))
    report.segments_found += len(segments)
    logger.debug("Channel %d: %d messages → %d segments", channel.id, len(raw_messages), len(segments))

    # Dedup all segments upfront — filter before hitting the LLM
    pending_segments = await _filter_duplicates(segments, report)
    if not pending_segments:
        return []

    # ONE batch LLM call for all pending segments
    try:
        extractions = await extract_segments_batch(pending_segments, existing_arc_tags)
    except LLMError as exc:
        logger.error("Batch extraction failed for channel %d: %s", channel.id, exc)
        report.segments_extraction_failed += len(pending_segments)
        return []

    # Embed + store each extracted chunk
    return await _store_batch_results(pending_segments, extractions, report)


# ---------------------------------------------------------------------------
# Public range-based ingestion (used by backfill script)
# ---------------------------------------------------------------------------

async def ingest_channel_range(
    channel: discord.TextChannel,
    after: datetime,
    before: datetime,
    report: IngestionReport,
    skip_arc_summary_triggers: bool = False,
) -> list[str]:
    """
    Ingest a specific date range from a channel.

    Public entry point used by the backfill script. The daily job uses
    run_ingestion() instead, which reads the window from config.

    Args:
        channel:                    Discord channel to fetch from.
        after:                      Fetch messages after this datetime (UTC, inclusive).
        before:                     Fetch messages before this datetime (UTC, inclusive).
        report:                     IngestionReport to accumulate stats into.
        skip_arc_summary_triggers:  If True, arc summaries are not triggered at the end.
                                    Useful when backfilling a large range — trigger manually
                                    after all chunks are loaded.

    Returns:
        List of arc tags that received new chunks (for arc summary trigger checking by caller).
    """
    cfg = get_config().rag
    existing_arc_tags = await get_distinct_arc_tags()

    raw_messages = await _fetch_messages(channel, after, cfg.min_message_length_words, before=before)
    if not raw_messages:
        return []

    segments = _segment_messages(raw_messages, cfg.conversation_gap_minutes, str(channel.id))
    report.segments_found += len(segments)
    logger.info(
        "Range ingestion: %d messages → %d segments for channel %s (%s → %s)",
        len(raw_messages), len(segments), channel.id,
        after.strftime("%Y-%m-%d"), before.strftime("%Y-%m-%d"),
    )

    # Dedup upfront
    pending_segments = await _filter_duplicates(segments, report)
    if not pending_segments:
        logger.info("All segments already ingested — nothing new to process.")
        return []

    logger.info(
        "%d/%d segments are new (not yet ingested). Sending to batch extractor...",
        len(pending_segments), len(segments),
    )

    # ONE batch LLM call for the entire date range
    try:
        extractions = await extract_segments_batch(pending_segments, existing_arc_tags)
    except LLMError as exc:
        logger.error("Batch extraction failed: %s", exc)
        report.segments_extraction_failed += len(pending_segments)
        raise

    arc_tags_used = await _store_batch_results(pending_segments, extractions, report)

    if not skip_arc_summary_triggers and arc_tags_used:
        arc_stats = await get_arc_tag_stats(list(set(arc_tags_used)))
        await _check_arc_summary_triggers(arc_stats)

    return arc_tags_used


# ---------------------------------------------------------------------------
# Deduplication helper
# ---------------------------------------------------------------------------

async def _filter_duplicates(
    segments: list[MessageSegment],
    report: IngestionReport,
) -> list[MessageSegment]:
    """
    Check all segments against the DB and return only those not yet ingested.
    Updates report.segments_skipped_duplicate in place.
    """
    pending: list[MessageSegment] = []
    for segment in segments:
        if await find_existing_by_message_ids(segment.message_ids):
            report.segments_skipped_duplicate += 1
            logger.debug(
                "Segment starting %s already ingested. Skipping.",
                segment.start_time.isoformat(),
            )
        else:
            pending.append(segment)
    return pending


# ---------------------------------------------------------------------------
# Post-extraction: embed + store loop
# ---------------------------------------------------------------------------

async def _store_batch_results(
    segments: list[MessageSegment],
    extractions: list[Optional[ExtractionResult]],
    report: IngestionReport,
) -> list[str]:
    """
    Take the batch extraction results and, for each non-None result,
    embed → contradiction check → store → queue suggested tags.

    Returns the arc: tags used across all stored chunks (for arc trigger checking).
    """
    arc_tags_used: list[str] = []

    for segment, extraction in zip(segments, extractions):
        if extraction is None:
            report.segments_skipped_not_worth_storing += 1
            continue

        arc_tags = await _embed_and_store(segment, extraction, report)
        arc_tags_used.extend(arc_tags)

    return arc_tags_used


async def _embed_and_store(
    segment: MessageSegment,
    extraction: ExtractionResult,
    report: IngestionReport,
) -> list[str]:
    """
    Embed a single extraction result and store it. Handles contradiction check.

    Returns the arc: tags found in this chunk (empty list if store fails).
    """
    chunk_id = str(uuid.uuid4())
    doc = RAGDocument(
        id=chunk_id,
        doc_type=extraction.doc_type,
        suggested_doc_type=extraction.suggested_doc_type,
        summary=extraction.summary,
        key_quotes=extraction.key_quotes,
        tags=extraction.tags,
        suggested_tags=extraction.suggested_tags,
        suggestion_justifications=extraction.suggestion_justifications,
        free_labels=extraction.free_labels,
        individuals=extraction.individuals,
        significance=extraction.significance,
        sentiment=extraction.sentiment,
        event_date=extraction.event_date,
        related_chunk_ids=extraction.related_chunk_ids,
        source_channel_id=segment.channel_id,
        source_message_ids=segment.message_ids,
    )

    # Embed — fail hard if Ollama is unavailable (user's explicit choice)
    try:
        doc.embedding = await embed_text(doc.embedding_text())
    except LLMError as exc:
        raise LLMError(
            f"Embedding failed for chunk from segment starting {segment.start_time.isoformat()}. "
            f"Ollama must be running with nomic-embed-text. Error: {exc}"
        ) from exc

    # Contradiction check (only for fact chunks)
    if extraction.doc_type == DocType.FACT and extraction.individuals:
        existing_facts = await find_active_facts_for_individuals(extraction.individuals)
        if existing_facts:
            contradiction_detected, contradicted_id = await check_contradiction(
                new_fact_summary=extraction.summary,
                new_fact_id=chunk_id,
                existing_facts=existing_facts,
            )
            if contradiction_detected and contradicted_id:
                doc.potential_contradiction = True
                report.contradictions_flagged += 1
                logger.info(
                    "Contradiction flagged: new chunk %s may conflict with existing chunk %s",
                    chunk_id,
                    contradicted_id,
                )

    # Store
    await insert_document(doc)
    report.chunks_stored += 1

    # Queue suggested tags for human review
    if extraction.suggested_tags:
        await store_suggested_tags(
            chunk_id, extraction.suggested_tags, extraction.suggestion_justifications
        )

    return [t for t in doc.tags if t.startswith("arc:")]


# ---------------------------------------------------------------------------
# Message fetching
# ---------------------------------------------------------------------------

async def _fetch_messages(
    channel: discord.TextChannel,
    after: datetime,
    min_words: int,
    before: Optional[datetime] = None,
) -> list[RawMessage]:
    """
    Fetch messages from a channel within a time window.

    Filters out:
    - Messages from bots (other than Ghost herself — Ghost's messages matter)
    - Messages shorter than min_words words
    - Messages with empty content (e.g. embed-only)

    Args:
        channel:  Channel to fetch from.
        after:    Only include messages after this datetime.
        min_words: Minimum word count to include a message.
        before:   If set, only include messages before this datetime.
    """
    raw: list[RawMessage] = []

    kwargs: dict = {"after": after, "oldest_first": True, "limit": None}
    if before is not None:
        kwargs["before"] = before

    async for msg in channel.history(**kwargs):
        # Exclude messages from other bots (not Ghost)
        if msg.author.bot and msg.author != channel.guild.me:
            continue

        content = msg.content.strip()
        if not content:
            continue
        if len(content.split()) < min_words:
            continue

        raw.append(RawMessage(
            message_id=str(msg.id),
            author_name=msg.author.display_name or msg.author.name,
            author_id=str(msg.author.id),
            content=content,
            timestamp=msg.created_at.replace(tzinfo=timezone.utc),
            is_bot=msg.author.bot,
        ))

    return raw


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def _segment_messages(
    messages: list[RawMessage],
    gap_minutes: int,
    channel_id: str,
) -> list[MessageSegment]:
    """
    Group messages into conversation segments.

    A new segment starts whenever the gap between consecutive messages
    exceeds gap_minutes. Each segment must have at least 2 messages to
    be worth extracting (a single isolated message rarely forms a complete unit).
    """
    if not messages:
        return []

    segments: list[MessageSegment] = []
    current_batch: list[RawMessage] = [messages[0]]
    gap = timedelta(minutes=gap_minutes)

    for msg in messages[1:]:
        if msg.timestamp - current_batch[-1].timestamp > gap:
            if len(current_batch) >= 2:
                segments.append(MessageSegment(messages=current_batch, channel_id=channel_id))
            current_batch = [msg]
        else:
            current_batch.append(msg)

    if len(current_batch) >= 2:
        segments.append(MessageSegment(messages=current_batch, channel_id=channel_id))

    return segments


# ---------------------------------------------------------------------------
# Arc summary trigger check
# ---------------------------------------------------------------------------

async def _check_arc_summary_triggers(arc_stats) -> list[str]:
    """
    Evaluate arc stats and trigger arc summary generation where conditions are met.

    Conditions (either triggers summarisation):
        1. estimated_total_tokens >= arc_summary_token_threshold
        2. days_since_last_ingestion >= arc_closure_gap_days

    Returns list of arc tags for which summaries were triggered.
    """
    from .arc_agent import generate_arc_summary

    cfg = get_config().rag
    triggered: list[str] = []

    for stats in arc_stats:
        size_trigger = stats.estimated_total_tokens >= cfg.arc_summary_token_threshold
        closure_trigger = (
            stats.days_since_last_ingestion is not None
            and stats.days_since_last_ingestion >= cfg.arc_closure_gap_days
        )

        if not (size_trigger or closure_trigger):
            continue

        reason = "size threshold exceeded" if size_trigger else "closure gap exceeded"
        logger.info(
            "Arc summary trigger for %s (%s). Tokens: ~%d, Days since last: %s",
            stats.arc_tag,
            reason,
            stats.estimated_total_tokens,
            f"{stats.days_since_last_ingestion:.1f}" if stats.days_since_last_ingestion else "unknown",
        )

        try:
            await generate_arc_summary(stats.arc_tag)
            triggered.append(stats.arc_tag)
        except Exception as exc:
            logger.error("Arc summary generation failed for %s: %s", stats.arc_tag, exc)

    return triggered
