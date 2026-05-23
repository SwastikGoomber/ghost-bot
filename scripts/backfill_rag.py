"""
scripts/backfill_rag.py — Backfill the RAG pipeline with historical Discord messages.

Connects to Discord and MongoDB, fetches messages from a channel between two dates,
and runs them through the full RAG pipeline (segment → extract → embed → store).

Usage:
    uv run scripts/backfill_rag.py --channel <CHANNEL_ID> --start <YYYY-MM-DD> --end <YYYY-MM-DD>

Examples:
    # Ingest all of April 2026 from channel 1234567890
    uv run scripts/backfill_rag.py --channel 1234567890 --start 2026-04-01 --end 2026-04-30

    # Dry run — shows what would be processed without storing anything
    uv run scripts/backfill_rag.py --channel 1234567890 --start 2026-01-01 --end 2026-04-30 --dry-run

    # Skip arc summary triggers (useful for large bulk loads — trigger manually after)
    uv run scripts/backfill_rag.py --channel 1234567890 --start 2025-01-01 --end 2026-04-30 --skip-arc-summaries

Options:
    --channel         Discord channel ID (required)
    --start           Start date inclusive, YYYY-MM-DD (required)
    --end             End date inclusive, YYYY-MM-DD (required)
    --batch-days      Days per batch [default: 7]. Larger = fewer API calls but more memory.
    --dry-run         Fetch and segment only — do not call LLM or store anything
    --skip-arc-summaries  Do not trigger arc summary generation after ingestion
    --force           Ignore deduplication — re-process already-ingested message IDs

Notes:
    - Requires DISCORD_TOKEN, GEMINI_API_KEY, MONGODB_URI in .env
    - Requires Ollama running with mxbai-embed-large pulled
    - Run from the project root: uv run scripts/backfill_rag.py ...
    - The script processes messages in batches to avoid memory pressure and Discord rate limits
    - Deduplication is active by default — re-running the same range is safe
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root setup — must happen before any bot.* imports
# ---------------------------------------------------------------------------
# The script lives in scripts/ but needs bot.* imports. Add the project root
# to sys.path so Python can resolve the bot package correctly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import discord

from bot.utils.logging import setup_logging, get_logger
from bot.utils.config import get_config
from bot.utils.exceptions import LLMError, DatabaseError
from bot.memory import db as mongo
from bot.memory.rag import create_indexes, ingest_channel_range
from bot.memory.rag.models import IngestionReport

setup_logging()
logger = get_logger("backfill_rag")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill the RAG pipeline with historical Discord messages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--channel",
        type=int,
        required=True,
        metavar="CHANNEL_ID",
        help="Discord channel ID to ingest from",
    )
    parser.add_argument(
        "--start",
        required=True,
        metavar="YYYY-MM-DD",
        help="Start date (inclusive)",
    )
    parser.add_argument(
        "--end",
        required=True,
        metavar="YYYY-MM-DD",
        help="End date (inclusive)",
    )
    parser.add_argument(
        "--batch-days",
        type=int,
        default=7,
        metavar="N",
        help="Days per processing batch (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and segment only — no LLM calls, no storage",
    )
    parser.add_argument(
        "--skip-arc-summaries",
        action="store_true",
        help="Skip arc summary triggers after ingestion (useful for large bulk loads)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore deduplication — re-process already-ingested message IDs",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args: argparse.Namespace) -> None:
    # Parse dates
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    except ValueError as exc:
        print(f"ERROR: Invalid date format — {exc}")
        sys.exit(1)

    if start_date > end_date:
        print("ERROR: --start must be before --end")
        sys.exit(1)

    total_days = (end_date - start_date).days + 1
    print(f"\n{'='*60}")
    print(f"Ghost Bot — RAG Backfill Script")
    print(f"{'='*60}")
    print(f"  Channel:     {args.channel}")
    print(f"  Range:       {args.start} → {args.end}  ({total_days} days)")
    print(f"  Batch size:  {args.batch_days} days")
    print(f"  Dry run:     {args.dry_run}")
    print(f"  Skip arcs:   {args.skip_arc_summaries}")
    print(f"  Force:       {args.force}")
    print(f"{'='*60}\n")

    # Validate config
    cfg = get_config()

    # Connect MongoDB
    print("Connecting to MongoDB...")
    try:
        await mongo.connect()
        print("  MongoDB connected.")
    except DatabaseError as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)

    if not args.dry_run:
        await create_indexes()
        print("  Indexes verified.\n")

    # Connect Discord
    print("Connecting to Discord (this may take a few seconds)...")
    client = discord.Client(intents=_build_intents())
    channel_ref: dict = {}  # mutable container for channel, set inside on_ready

    @client.event
    async def on_ready():
        print(f"  Discord ready: {client.user}\n")
        try:
            await _run_backfill(client, args, start_date, end_date, channel_ref, cfg)
        finally:
            await client.close()

    import os
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN not set in .env")
        await mongo.close()
        sys.exit(1)

    try:
        await client.start(token)
    except discord.LoginFailure:
        print("ERROR: Discord login failed — check DISCORD_TOKEN")
        sys.exit(1)
    finally:
        await mongo.close()


# ---------------------------------------------------------------------------
# Backfill logic
# ---------------------------------------------------------------------------

async def _run_backfill(
    client: discord.Client,
    args: argparse.Namespace,
    start_date: datetime,
    end_date: datetime,
    channel_ref: dict,
    cfg,
) -> None:
    # Fetch channel (API call — works even if not in cache)
    try:
        channel = await client.fetch_channel(args.channel)
    except discord.NotFound:
        print(f"ERROR: Channel {args.channel} not found.")
        return
    except discord.Forbidden:
        print(f"ERROR: Bot does not have access to channel {args.channel}.")
        return

    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        print(f"ERROR: Channel {args.channel} is not a text channel.")
        return

    print(f"Channel: #{channel.name} (in {channel.guild.name})")
    print()

    # Accumulate totals across all batches
    total_report = IngestionReport()
    batch_num = 0
    batch_start = start_date

    while batch_start <= end_date:
        batch_end = min(batch_start + timedelta(days=args.batch_days - 1, hours=23, minutes=59, seconds=59), end_date)
        batch_num += 1

        batch_start_str = batch_start.strftime("%Y-%m-%d")
        batch_end_str = batch_end.strftime("%Y-%m-%d")

        print(f"[Batch {batch_num}] {batch_start_str} → {batch_end_str}", end=" ", flush=True)

        if args.dry_run:
            count = await _dry_run_batch(channel, batch_start, batch_end, cfg)
            print(f"→ ~{count} qualifying messages (dry run, not stored)")
        else:
            batch_report = IngestionReport()
            try:
                await ingest_channel_range(
                    channel=channel,
                    after=batch_start,
                    before=batch_end,
                    report=batch_report,
                    skip_arc_summary_triggers=args.skip_arc_summaries,
                )
            except LLMError as exc:
                print(f"\n  FATAL: {exc}")
                print("  Ensure Ollama is running: ollama serve && ollama pull nomic-embed-large")
                _print_total_report(total_report)
                return

            _accumulate(total_report, batch_report)
            print(
                f"→ segments:{batch_report.segments_found} "
                f"stored:{batch_report.chunks_stored} "
                f"skipped:{batch_report.segments_skipped_duplicate + batch_report.segments_skipped_not_worth_storing} "
                f"contradictions:{batch_report.contradictions_flagged}"
            )

        batch_start = batch_end + timedelta(seconds=1)

    print()
    _print_total_report(total_report)

    if not args.dry_run and args.skip_arc_summaries:
        print("\nNote: arc summary triggers were skipped.")
        print("To trigger arc summaries for all arcs manually, run:")
        print("  uv run scripts/trigger_arc_summaries.py  (not yet implemented)")


async def _dry_run_batch(
    channel: discord.TextChannel,
    after: datetime,
    before: datetime,
    cfg,
) -> int:
    """Fetch and count qualifying messages without processing them."""
    from bot.memory.rag.models import RawMessage
    from bot.memory.rag.ingestion import _fetch_messages, _segment_messages

    messages = await _fetch_messages(
        channel,
        after,
        cfg.rag.min_message_length_words,
        before=before,
    )
    segments = _segment_messages(messages, cfg.rag.conversation_gap_minutes, str(channel.id))
    return len(messages)


def _accumulate(total: IngestionReport, batch: IngestionReport) -> None:
    total.channels_processed = 1
    total.segments_found += batch.segments_found
    total.segments_skipped_duplicate += batch.segments_skipped_duplicate
    total.segments_skipped_not_worth_storing += batch.segments_skipped_not_worth_storing
    total.segments_extraction_failed += batch.segments_extraction_failed
    total.chunks_stored += batch.chunks_stored
    total.contradictions_flagged += batch.contradictions_flagged
    total.arc_summaries_triggered.extend(batch.arc_summaries_triggered)


def _print_total_report(report: IngestionReport) -> None:
    print(f"{'='*60}")
    print(f"  Backfill complete")
    print(f"{'='*60}")
    print(f"  Segments found:            {report.segments_found}")
    print(f"  Chunks stored:             {report.chunks_stored}")
    print(f"  Skipped (duplicate):       {report.segments_skipped_duplicate}")
    print(f"  Skipped (not worth store): {report.segments_skipped_not_worth_storing}")
    print(f"  Extraction failures:       {report.segments_extraction_failed}")
    print(f"  Contradictions flagged:    {report.contradictions_flagged}")
    if report.arc_summaries_triggered:
        print(f"  Arc summaries triggered:   {', '.join(report.arc_summaries_triggered)}")
    print(f"{'='*60}\n")


def _build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    return intents


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
