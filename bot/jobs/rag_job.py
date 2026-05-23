"""
Daily RAG ingestion job entry point.

This module is the boundary between the scheduler and the ingestion pipeline.
Its only job is to call run_ingestion() with the right dependencies and handle
any top-level exceptions that shouldn't crash the scheduler.

Error handling policy:
  - LLMError from Ollama being down: log as CRITICAL and abort the run.
    The user explicitly chose "fail hard if Ollama is unavailable."
  - DatabaseError: log as CRITICAL, abort the run.
  - Any other unexpected exception: log as ERROR with traceback, abort the run.
  - The scheduler will retry on the next scheduled run regardless of failure.
"""

from __future__ import annotations

import logging

import discord

from bot.utils.exceptions import LLMError, DatabaseError
from bot.utils.logging import get_logger
from bot.memory.rag import run_ingestion

logger = get_logger(__name__)


async def run_rag_job(discord_client: discord.Client) -> None:
    """
    Execute the daily RAG ingestion run.

    Called by RAGScheduler._run_rag(). Never raises — all exceptions are caught
    and logged so the scheduler remains alive for future runs.

    Args:
        discord_client: The live GhostDiscordBot instance.
    """
    logger.info("=== RAG Daily Ingestion Job: START ===")

    try:
        report = await run_ingestion(discord_client)

        logger.info(
            "=== RAG Daily Ingestion Job: COMPLETE === "
            "channels=%d segments_found=%d stored=%d "
            "duplicates_skipped=%d not_worth_storing=%d extraction_failed=%d "
            "contradictions_flagged=%d arc_summaries_triggered=%s",
            report.channels_processed,
            report.segments_found,
            report.chunks_stored,
            report.segments_skipped_duplicate,
            report.segments_skipped_not_worth_storing,
            report.segments_extraction_failed,
            report.contradictions_flagged,
            report.arc_summaries_triggered,
        )

    except LLMError as exc:
        logger.critical(
            "RAG ingestion ABORTED: Ollama is unavailable or embedding failed. "
            "Ensure Ollama is running with 'ollama serve' and nomic-embed-text is pulled "
            "('ollama pull nomic-embed-text'). Error: %s",
            exc,
        )

    except DatabaseError as exc:
        logger.critical(
            "RAG ingestion ABORTED: Database error. "
            "Check MongoDB connection and collection state. Error: %s",
            exc,
        )

    except Exception as exc:
        logger.error(
            "RAG ingestion ABORTED: Unexpected error.",
            exc_info=True,
        )
