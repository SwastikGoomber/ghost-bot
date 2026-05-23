"""
MongoDB singleton client.

A single AsyncIOMotorClient is shared by all modules (memory, RAG, etc.).
Call get_db() anywhere to receive the ghost_bot database handle.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect() -> None:
    """Initialise the motor client. Call once at startup."""
    global _client, _db

    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise DatabaseError("MONGODB_URI environment variable is not set.")

    _client = AsyncIOMotorClient(uri)
    _db = _client.ghost_bot

    # Confirm connectivity
    try:
        await _db.command("ping")
        logger.info("Connected to MongoDB.")
    except Exception as exc:
        _client = None
        _db = None
        raise DatabaseError(f"MongoDB ping failed: {exc}") from exc


async def close() -> None:
    """Gracefully close the motor client."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """Return the ghost_bot database handle. Raises if not yet connected."""
    if _db is None:
        raise DatabaseError(
            "Database is not connected. Call memory.db.connect() during initialisation."
        )
    return _db


async def ping() -> bool:
    """Health-check. Returns True if MongoDB is reachable."""
    try:
        if _db is None:
            return False
        await _db.command("ping")
        return True
    except Exception:
        return False
