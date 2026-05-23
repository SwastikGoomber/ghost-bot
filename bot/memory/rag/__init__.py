"""
RAG (Retrieval-Augmented Generation) package.

Public surface:
    run_ingestion(discord_client)  — daily ingestion entry point
    retrieve(query)                — hybrid retrieval, returns list[RetrievedChunk]
    format_for_injection(chunks)   — render retrieved chunks for context injection
    create_indexes()               — idempotent MongoDB index creation (call at startup)
"""

from .ingestion import run_ingestion, ingest_channel_range
from .retriever import retrieve, format_for_injection
from .store import create_indexes

__all__ = [
    "run_ingestion",
    "ingest_channel_range",
    "retrieve",
    "format_for_injection",
    "create_indexes",
]
