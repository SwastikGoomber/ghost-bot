"""
Memory package.

Public surface:
    StateManager  — user state, persistence, summaries, account linking
    db            — low-level MongoDB helpers (connect, close, ping)
    rag           — RAG pipeline (ingestion, retrieval, arc summarisation)
"""

from .state import StateManager
from . import db
from . import rag

__all__ = ["StateManager", "db", "rag"]
