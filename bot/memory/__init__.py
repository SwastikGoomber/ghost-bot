"""
Memory package.

Public surface:
    StateManager  — user state, persistence, summaries, account linking
    db            — low-level MongoDB helpers (connect, close, ping)
"""

from .state import StateManager
from . import db

__all__ = ["StateManager", "db"]
