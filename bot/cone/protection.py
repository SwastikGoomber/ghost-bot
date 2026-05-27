"""
Protected-span handling for cone transforms.

Cone effects should alter normal speech, not platform syntax. Mentions, links,
and emotes are temporarily replaced before a transform runs and restored after.
"""

from __future__ import annotations

import re
from collections.abc import Callable


_PROTECTED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"!\[[^\]]*]\([^)\s]+(?:\s+\"[^\"]*\")?\)"),  # Markdown image
    re.compile(r"\[[^\]]+]\([^)\s]+(?:\s+\"[^\"]*\")?\)"),   # Markdown link
    re.compile(r"https?://[^\s<>()]+"),
    re.compile(r"<a?:[A-Za-z0-9_~]+:\d+>"),                 # Discord custom emoji
    re.compile(r"<@!?\d+>|<@&\d+>|<#\d+>"),                 # Discord mentions/channels/roles
    re.compile(r"@[A-Za-z0-9_.-]{2,32}"),                   # Plain @ pings
    re.compile(r":[A-Za-z0-9_~]{2,64}:"),                   # Colon emote aliases
    re.compile(
        "["
        "\U0001F1E6-\U0001F1FF"
        "\U0001F300-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U00002600-\U000026FF"
        "](?:\ufe0f|\u200d["
        "\U0001F1E6-\U0001F1FF"
        "\U0001F300-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U00002600-\U000026FF"
        "])*"
    ),
)


def apply_with_protected_spans(text: str, transform: Callable[[str], str]) -> str:
    """Apply a transform while preserving platform syntax exactly."""
    if not text:
        return transform(text)

    protected = _collect_protected_spans(text)
    if not protected:
        return transform(text)

    placeholders: dict[str, str] = {}
    parts: list[str] = []
    cursor = 0
    for index, (start, end) in enumerate(protected):
        placeholder = f"\x1f{index}\x1f"
        placeholders[placeholder] = text[start:end]
        parts.append(text[cursor:start])
        parts.append(placeholder)
        cursor = end
    parts.append(text[cursor:])

    transformed = transform("".join(parts))
    for placeholder, original in placeholders.items():
        transformed = transformed.replace(placeholder + placeholder[:2], original)
        transformed = transformed.replace(placeholder, original)
    return transformed


def _collect_protected_spans(text: str) -> list[tuple[int, int]]:
    matches: list[tuple[int, int]] = []
    for pattern in _PROTECTED_PATTERNS:
        matches.extend((m.start(), m.end()) for m in pattern.finditer(text))

    matches.sort(key=lambda span: (span[0], -(span[1] - span[0])))

    protected: list[tuple[int, int]] = []
    current_end = -1
    for start, end in matches:
        if start < current_end:
            continue
        protected.append((start, end))
        current_end = end
    return protected
