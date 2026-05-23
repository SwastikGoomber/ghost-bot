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

    # Enable DEBUG for pipeline and LLM layers so Ollama calls are visible
    logging.getLogger("bot.pipeline").setLevel(logging.DEBUG)
    logging.getLogger("bot.utils.llm").setLevel(logging.DEBUG)
    logging.getLogger("bot.memory.rag").setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call with __name__ from any module."""
    return logging.getLogger(name)


def redact_system_prompt(prompt: str) -> str:
    """
    Redacts continuous blocks of text inside system prompt sections,
    preserving headers, structures, and snippet boundaries.
    """
    if not prompt:
        return ""

    # Split by \n\n (which is how ContextBuilder joins sections, and how markdown templates separate sections)
    parts = prompt.split("\n\n")
    redacted_parts = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        lines = part.split("\n")
        first_line = lines[0].strip()

        # If the block is short, keep it fully intact
        if len(part) <= 250:
            redacted_parts.append(part)
            continue

        # Dynamically determine a label/header for the block to keep logs highly readable
        label = "SYSTEM SECTION"
        if first_line.startswith("#"):
            label = first_line.lstrip("#").strip()
        elif first_line.startswith("[") and first_line.endswith("]"):
            label = first_line[1:-1].strip()
        elif ":" in first_line and len(first_line.split(":")[0]) < 40:
            label = first_line.split(":")[0].strip()

        # Snip the middle, keeping first 80 and last 80 characters
        first_part = part[:80].replace('\n', ' ')
        last_part = part[-80:].replace('\n', ' ')
        redacted_len = len(part) - 160

        redacted_parts.append(
            f"[{label.upper()}] {first_part} ... [{redacted_len} chars redacted] ... {last_part}"
        )

    return "\n\n".join(redacted_parts)


def redact_messages(messages: list[dict]) -> list[dict]:
    """Redacts long messages in conversation history."""
    redacted = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            redacted.append({"role": role, "content": ""})
            continue

        if len(content) <= 150:
            redacted_content = content.replace('\n', ' ')
        else:
            first_part = content[:70].replace('\n', ' ')
            last_part = content[-70:].replace('\n', ' ')
            redacted_content = f"{first_part} ... [{len(content) - 140} chars redacted] ... {last_part}"

        redacted.append({"role": role, "content": redacted_content})
    return redacted


def log_llm_call(
    client_name: str,
    model: str,
    system_prompt: str,
    messages: list[dict],
    response: str,
    extra_info: str = "",
) -> None:
    """Logs a clean, visually boxed and redacted LLM interaction."""
    redacted_sys = redact_system_prompt(system_prompt)
    redacted_msgs = redact_messages(messages)

    msgs_str = "\n".join(f"    - {msg['role']}: {msg['content']}" for msg in redacted_msgs)

    log_msg = (
        f"\n==================== LLM CALL START ====================\n"
        f"Client: {client_name} ({model})\n"
        f"Extra:  {extra_info}\n"
        f"-------------------- SYSTEM PROMPT --------------------\n"
        f"{redacted_sys}\n"
        f"-------------------- HISTORY WINDOW --------------------\n"
        f"{msgs_str}\n"
        f"-------------------- RESPONSE OUTPUT --------------------\n"
        f"{response.strip()}\n"
        f"==================== LLM CALL END ===================="
    )
    # Log at INFO level to guarantee visibility in logs/ghost.log
    logging.getLogger("bot.utils.logging").info(log_msg)

