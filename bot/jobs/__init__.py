"""
Jobs package — scheduled background tasks.

Public surface:
    RAGScheduler  — wraps APScheduler, registers and manages the daily ingestion job
"""

from .scheduler import RAGScheduler

__all__ = ["RAGScheduler"]
