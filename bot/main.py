"""
Ghost Bot v2 — entry point.

Initialisation order:
    1. Load .env file (environment variables)
    2. Logging
    3. Config validation (fail fast if config.yaml is missing/broken)
    4. MongoDB connection
    5. Load persistent state (user states, cone data)
    6. Load special users
    7. Build shared objects (StateManager, ConeManager, ContextBuilder)
    8. Build RAG scheduler (if rag.enabled) and attach to Discord bot
    9. Start Discord and Twitch bots concurrently
    10. Discord on_ready starts the scheduler once the bot is live
    11. Graceful shutdown on SIGINT / SIGTERM
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root BEFORE any other imports
load_dotenv()

from .utils.logging import setup_logging, get_logger
from .utils.config import get_config
from .utils.exceptions import ConfigError, DatabaseError
from .memory import db as mongo
from .memory.state import StateManager
from .memory.rag import create_indexes as rag_create_indexes
from .cone.manager import ConeManager
from .pipeline.context import ContextBuilder
from .platforms.discord_bot import GhostDiscordBot
from .platforms.twitch_bot import GhostTwitchBot
from .jobs.scheduler import RAGScheduler

# Set up logging before anything else
setup_logging()
logger = get_logger(__name__)

_shutdown_event = asyncio.Event()


def _handle_signal(sig, frame) -> None:
    logger.info("Received signal %s — initiating shutdown.", sig)
    _shutdown_event.set()


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

async def _initialise() -> tuple[GhostDiscordBot, GhostTwitchBot, Optional[RAGScheduler]]:
    """Build and wire all shared components. Returns the two bot instances and optional scheduler."""

    # Config
    logger.info("Loading configuration...")
    cfg = get_config()
    logger.info("Configuration loaded. Chat model: %s", cfg.models.chat)

    # Validate required environment variables early (fail fast)
    _assert_env("DISCORD_TOKEN")
    _assert_env("GEMINI_API_KEY")
    if os.environ.get("MONGODB_URI"):
        logger.info("MongoDB URI found — using MongoDB for state persistence.")
    else:
        logger.warning("MONGODB_URI not set — state will be persisted to local JSON file.")

    # MongoDB
    if os.environ.get("MONGODB_URI"):
        logger.info("Connecting to MongoDB...")
        await mongo.connect()
        # Create RAG collection indexes (idempotent)
        if cfg.rag.enabled:
            logger.info("Creating RAG collection indexes...")
            await rag_create_indexes()

    # State manager + load persistent state
    logger.info("Initialising state manager...")
    state_manager = StateManager()
    await state_manager.load_states()

    # Load special users (static lore data)
    special_users = state_manager.load_special_users()
    logger.info("Loaded %d special users.", len(special_users))

    # Shared objects
    cone_manager = ConeManager(state_manager)
    context_builder = ContextBuilder(special_users)

    # Bots
    discord_bot = GhostDiscordBot(state_manager, cone_manager, context_builder)
    twitch_bot = GhostTwitchBot(state_manager, cone_manager, context_builder)

    # RAG Scheduler — attach to Discord bot so it starts after on_ready
    rag_scheduler: Optional[RAGScheduler] = None
    if cfg.rag.enabled:
        if not os.environ.get("MONGODB_URI"):
            logger.warning(
                "RAG is enabled but MONGODB_URI is not set. "
                "RAG ingestion requires MongoDB — scheduler will not start."
            )
        else:
            rag_scheduler = RAGScheduler(discord_bot)
            discord_bot._rag_scheduler = rag_scheduler
            logger.info("RAG scheduler created. Will start after Discord on_ready.")
    else:
        logger.info("RAG is disabled (rag.enabled=false). Scheduler not created.")

    return discord_bot, twitch_bot, rag_scheduler


def _assert_env(name: str) -> None:
    if not os.environ.get(name):
        raise ConfigError(f"Required environment variable '{name}' is not set.")


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------

async def _shutdown(
    discord_bot: Optional[GhostDiscordBot] = None,
    twitch_bot: Optional[GhostTwitchBot] = None,
    rag_scheduler: Optional[RAGScheduler] = None,
) -> None:
    logger.info("Shutting down...")

    # Stop scheduler first so no new jobs start during shutdown
    if rag_scheduler is not None:
        await rag_scheduler.shutdown()

    tasks = []
    if discord_bot:
        tasks.append(asyncio.create_task(discord_bot.close()))
    if twitch_bot:
        tasks.append(asyncio.create_task(twitch_bot.close()))

    if tasks:
        done, pending = await asyncio.wait(tasks, timeout=5)
        if pending:
            logger.warning("%d shutdown tasks did not complete in time.", len(pending))

    await mongo.close()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    discord_bot: Optional[GhostDiscordBot] = None
    twitch_bot: Optional[GhostTwitchBot] = None
    rag_scheduler: Optional[RAGScheduler] = None

    try:
        discord_bot, twitch_bot, rag_scheduler = await _initialise()

        discord_token = os.environ["DISCORD_TOKEN"]
        twitch_token = os.environ.get("TWITCH_TOKEN")

        logger.info("Starting bots...")
        active_tasks = [asyncio.create_task(discord_bot.start(discord_token))]

        if twitch_token:
            active_tasks.append(asyncio.create_task(twitch_bot.start()))
        else:
            logger.warning("TWITCH_TOKEN not set — Twitch bot will not start.")

        shutdown_task = asyncio.create_task(_shutdown_event.wait())

        while active_tasks:
            done, _ = await asyncio.wait(
                active_tasks + [shutdown_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if shutdown_task in done:
                logger.info("Shutdown requested.")
                break

            for task in list(done):
                if task not in active_tasks:
                    continue
                exc = task.exception()
                if exc:
                    logger.error("Bot task failed: %s", exc, exc_info=exc)
                    # Discord failure is fatal; Twitch failure is recoverable
                    if task == active_tasks[0]:  # discord task is always first
                        raise exc
                    active_tasks.remove(task)
                    logger.warning("Twitch bot task ended — continuing with Discord only.")
                else:
                    active_tasks.remove(task)

            if not active_tasks:
                logger.warning("All bot tasks have stopped.")
                break

    except ConfigError as exc:
        logger.critical("Configuration error: %s", exc)
        sys.exit(1)
    except DatabaseError as exc:
        logger.critical("Database error during startup: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        raise
    finally:
        await _shutdown(discord_bot, twitch_bot, rag_scheduler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except SystemExit:
        raise
    except Exception:
        logger.critical("Bot crashed.", exc_info=True)
        sys.exit(1)
