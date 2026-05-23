"""
Advanced cone effects powered by spaCy.

A single AdvancedConeEffects instance is created at import time (module-level
singleton) so spaCy is loaded once at process startup — no lazy-loading, no
per-call overhead.

Public surface: apply_advanced_effect(text, effect) -> str | None
Returns None if the effect name is not handled here (caller falls back to basic.py).
"""

from __future__ import annotations

import sys
import importlib
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazily import the v1 advanced_cone_effects module from bot_v1/.
# We re-use the existing code rather than duplicating it.
# ---------------------------------------------------------------------------

_advanced: Optional[object] = None
_advanced_apply: Optional[Callable[[str, str], str]] = None


def _load_advanced() -> None:
    global _advanced, _advanced_apply
    try:
        # Add bot_v1/ to sys.path so the legacy module resolves correctly.
        # This is safe because we do it once at startup and the module is isolated.
        import os
        from pathlib import Path
        bot_v1_path = str(Path(__file__).resolve().parents[3] / "bot_v1")
        if bot_v1_path not in sys.path:
            sys.path.insert(0, bot_v1_path)

        from advanced_cone_effects import AdvancedConeEffects, apply_cone_effect  # type: ignore
        _advanced = AdvancedConeEffects()
        _advanced_apply = apply_cone_effect
        logger.info("Advanced cone effects (spaCy) loaded successfully.")
    except ImportError as exc:
        logger.warning("Could not load advanced_cone_effects: %s — advanced effects disabled.", exc)
    except OSError as exc:
        logger.warning("spaCy model not found: %s — advanced effects disabled.", exc)


# Load at module import time (called once when this module is first imported)
_load_advanced()


# Names that are exclusively handled by the advanced module
# (i.e. they have no basic.py equivalent)
_ADVANCED_ONLY_EFFECTS = frozenset({
    "slayspeak", "valley",
    "brainrot", "genz",
    "scrum", "corporate",
    "linkedin", "emoji",
    "crisis", "existential",
    "canadian", "polite",
    "vsauce", "conspiracy",
    "bri", "british",
    "oni", "censor",
    "dyslexia", "dickslexia",
})


def apply_advanced_effect(text: str, effect: str) -> Optional[str]:
    """
    Apply an advanced (spaCy-powered) cone effect.

    Returns transformed text, or None if this effect is not available
    (caller should fall back to a basic implementation or raise).
    """
    if _advanced_apply is None:
        return None
    if effect.lower() not in _ADVANCED_ONLY_EFFECTS:
        return None
    try:
        return _advanced_apply(text, effect.lower())
    except Exception as exc:
        logger.error("Advanced cone effect '%s' failed: %s", effect, exc)
        return None


def is_advanced_effect(effect: str) -> bool:
    """True if this effect name is exclusively handled by the advanced module."""
    return effect.lower() in _ADVANCED_ONLY_EFFECTS
