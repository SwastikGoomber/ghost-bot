"""
Centralised logging setup.

Call setup_logging() once at process start (in main.py).
All modules then call get_logger(__name__) to obtain a named logger.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    """Configure root logger with rotating file + console handlers."""
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "ghost.log"),
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    # Silence overly chatty third-party loggers
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("twitchio").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call with __name__ from any module."""
    return logging.getLogger(name)
