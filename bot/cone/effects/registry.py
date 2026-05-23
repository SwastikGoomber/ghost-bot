"""
Cone effects registry — the single source of truth for every available effect.

Rules:
- EFFECTS maps canonical effect names to their transform functions.
- ALIASES maps alternate names to canonical names.
- apply_effect() is the only public entry point; it dispatches correctly.
- The LLM tool schema is generated from EFFECTS.keys() automatically — no manual sync.

Adding a new effect:
    1. Add the transform function to basic.py or advanced.py.
    2. Add an entry to EFFECTS (or ALIASES if it's an alias).
    3. Done. Tool schemas auto-update.
"""

from __future__ import annotations

from typing import Callable

from ...utils.exceptions import ConeEffectNotFoundError
from .basic import (
    transform_uwu,
    transform_pirate,
    transform_shakespeare,
    transform_caveman,
    transform_drunk,
)
from .advanced import apply_advanced_effect, is_advanced_effect
from .protection import apply_with_protected_spans


# ---------------------------------------------------------------------------
# Primary effect registry
# ---------------------------------------------------------------------------

EFFECTS: dict[str, Callable[[str], str]] = {
    # Basic (no spaCy required)
    "uwu": transform_uwu,
    "pirate": transform_pirate,
    "shakespeare": transform_shakespeare,
    "caveman": transform_caveman,
    "drunk": transform_drunk,
    # Advanced (spaCy-powered, routed through advanced.py)
    "slayspeak": lambda t: apply_advanced_effect(t, "slayspeak") or t,
    # "brainrot": lambda t: apply_advanced_effect(t, "brainrot") or t,
    # "scrum": lambda t: apply_advanced_effect(t, "scrum") or t,
    # "linkedin": lambda t: apply_advanced_effect(t, "linkedin") or t,
    # "crisis": lambda t: apply_advanced_effect(t, "crisis") or t,
    "canadian": lambda t: apply_advanced_effect(t, "canadian") or t,
    "vsauce": lambda t: apply_advanced_effect(t, "vsauce") or t,
    "bri": lambda t: apply_advanced_effect(t, "bri") or t,
    "oni": lambda t: apply_advanced_effect(t, "oni") or t,
    "dyslexia": lambda t: apply_advanced_effect(t, "dyslexia") or t,
}

# Alternate names that map to a canonical effect
ALIASES: dict[str, str] = {
    "bardify": "shakespeare",
    "valley": "slayspeak",
    # "genz": "brainrot",
    # "corporate": "scrum",
    # "emoji": "linkedin",
    # "existential": "crisis",
    "polite": "canadian",
    "conspiracy": "vsauce",
    "british": "bri",
    "censor": "oni",
    "dickslexia": "dyslexia",
    "unga": "caveman",
    "drunkard": "drunk",
}

# Complete set of names the LLM may use (canonical + aliases)
ALL_EFFECT_NAMES: frozenset[str] = frozenset(EFFECTS.keys()) | frozenset(ALIASES.keys())

# Sorted list for use in LLM tool schemas and validation messages
EFFECT_NAMES_SORTED: list[str] = sorted(ALL_EFFECT_NAMES)


def resolve(effect: str) -> str:
    """Return the canonical effect name, resolving aliases. Raises ConeEffectNotFoundError if unknown."""
    name = effect.lower().strip()
    if name in EFFECTS:
        return name
    if name in ALIASES:
        return ALIASES[name]
    raise ConeEffectNotFoundError(
        f"Unknown cone effect '{effect}'. "
        f"Available effects: {', '.join(EFFECT_NAMES_SORTED)}"
    )


def apply_effect(text: str, effect: str) -> str:
    """
    Apply a cone effect to text.

    Resolves aliases automatically.
    Raises ConeEffectNotFoundError for unknown names.
    """
    canonical = resolve(effect)
    return apply_with_protected_spans(text, EFFECTS[canonical])
