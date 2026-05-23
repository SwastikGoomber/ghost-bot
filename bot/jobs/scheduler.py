"""
APScheduler setup for Ghost Bot v2.

Manages the lifecycle of all scheduled background jobs.
Currently hosts only the daily RAG ingestion job — more jobs can be added here.

Usage:
    scheduler = RAGScheduler(discord_client)
    scheduler.start()           # call after Discord bot is ready
    await scheduler.shutdown()  # call during graceful shutdown

The scheduler runs in the same event loop as the bots (AsyncIOScheduler).
"""

from __future__ import annotations

import logging
from typing import Optional

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.utils.config import get_config
from bot.utils.logging import get_logger

from .rag_job import run_rag_job

logger = get_logger(__name__)


class RAGScheduler:
    """
    Wraps APScheduler's AsyncIOScheduler for Ghost Bot's job system.

    Responsibility: register jobs, manage start/stop, and pass the correct
    dependencies (discord_client) into each job at run time.
    """

    def __init__(self, discord_client: discord.Client) -> None:
        self._discord_client = discord_client
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._registered = False

    def start(self) -> None:
        """
        Register all jobs and start the scheduler.

        Call this after the Discord bot has connected (on_ready or equivalent),
        so the discord_client is guaranteed to be live before the first job run.
        """
        cfg = get_config()

        if not cfg.rag.enabled:
            logger.info("RAG is disabled — no ingestion job registered.")
            return

        self._register_rag_job(cfg.rag.extraction_cron)
        self._scheduler.start()
        self._registered = True
        logger.info("Scheduler started. RAG ingestion cron: %s (UTC)", cfg.rag.extraction_cron)

    def _register_rag_job(self, cron_expr: str) -> None:
        """
        Register the daily RAG ingestion job.

        APScheduler CronTrigger format (6 fields): second minute hour day month day_of_week
        Default: "0 30 0 * * *" → every day at 00:30 UTC (6:00 AM IST)
        """
        parts = cron_expr.strip().split()
        if len(parts) == 6:
            second, minute, hour, day, month, day_of_week = parts
        elif len(parts) == 5:
            # Standard 5-field cron: minute hour day month day_of_week
            minute, hour, day, month, day_of_week = parts
            second = "0"
        else:
            logger.warning(
                "Invalid cron expression '%s' — defaulting to daily at 00:30 UTC.", cron_expr
            )
            second, minute, hour, day, month, day_of_week = "0", "30", "0", "*", "*", "*"

        trigger = CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )

        self._scheduler.add_job(
            func=self._run_rag,
            trigger=trigger,
            id="rag_daily_ingestion",
            name="RAG Daily Ingestion",
            replace_existing=True,
            misfire_grace_time=3600,  # Allow up to 1 hour late start (e.g. if bot was restarting)
        )
        logger.info("RAG ingestion job registered (ID: rag_daily_ingestion).")

    async def _run_rag(self) -> None:
        """APScheduler calls this. Delegates to the job module."""
        await run_rag_job(self._discord_client)

    async def shutdown(self) -> None:
        """Gracefully stop the scheduler. Call during bot shutdown."""
        if self._registered and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down.")

    def trigger_now(self) -> None:
        """
        Manually trigger the RAG ingestion job immediately.

        Useful for testing or manually forcing an ingestion run outside the schedule.
        Does not affect the regular scheduled run.
        """
        if not self._registered:
            logger.warning("Scheduler not started — cannot trigger job manually.")
            return
        self._scheduler.modify_job("rag_daily_ingestion", next_run_time=__import__("datetime").datetime.utcnow())
        logger.info("RAG ingestion job manually triggered.")
