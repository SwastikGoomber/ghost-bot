"""
Cone effects registry — the single source of truth for every available effect.

Rules:
- EFFECTS maps canonical effect names to their transform functions.
- ALIASES maps alternate names to canonical names.
- apply_effect() is the only public entry point; it dispatches correctly.
- The LLM tool schema is generated from EFFECTS.keys() automatically — no manual sync.

Adding a new effect:
    1. Create a dedicated effect file under effects/ (e.g. effects/shakespeare.py).
    2. Add an entry to EFFECTS (or ALIASES if it's an alias).
    3. Done. Tool schemas auto-update.
"""

from __future__ import annotations

from typing import Callable

from bot.utils.exceptions import ConeEffectNotFoundError
from bot.cone.effects.uwu import transform_uwu
from bot.cone.effects.pirate import transform_pirate
from bot.cone.effects.shakespeare import transform_shakespeare
from bot.cone.effects.caveman import apply_caveman, transform_caveman
from bot.cone.effects.drunk import transform_drunk
from bot.cone.effects.slayspeak import apply_slayspeak
from bot.cone.effects.brainrot import apply_brainrot
from bot.cone.effects.scrum import apply_scrum
from bot.cone.effects.linkedin import apply_linkedin
from bot.cone.effects.crisis import apply_crisis
from bot.cone.effects.canadian import apply_canadian
from bot.cone.effects.vsauce import apply_vsauce
from bot.cone.effects.british import apply_british
from bot.cone.effects.oni import apply_oni
from bot.cone.effects.dyslexia import apply_dyslexia
from bot.cone.protection import apply_with_protected_spans


# ---------------------------------------------------------------------------
# Primary effect registry
# ---------------------------------------------------------------------------

EFFECTS: dict[str, Callable[[str], str]] = {
    "uwu": transform_uwu,
    "pirate": transform_pirate,
    "shakespeare": transform_shakespeare,
    "caveman": lambda t: apply_caveman(t) or transform_caveman(t),
    "drunk": transform_drunk,
    "slayspeak": apply_slayspeak,
    # "brainrot": apply_brainrot,
    # "scrum": apply_scrum,
    # "linkedin": apply_linkedin,
    # "crisis": apply_crisis,
    "canadian": apply_canadian,
    "vsauce": apply_vsauce,
    "bri": apply_british,
    "oni": apply_oni,
    "dyslexia": apply_dyslexia,
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

_ADVANCED_EFFECTS = frozenset({
    "slayspeak", "valley",
    "canadian", "polite",
    "vsauce", "conspiracy",
    "bri", "british",
    "oni", "censor",
    "dyslexia", "dickslexia",
    "caveman", "unga",
})


def is_advanced_effect(effect: str) -> bool:
    """True if this effect name uses spaCy features internally."""
    return effect.lower() in _ADVANCED_EFFECTS


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
