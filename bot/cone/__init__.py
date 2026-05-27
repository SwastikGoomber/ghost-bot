"""
Cone system package.

Public surface:
    ConeManager          — apply, remove, check cones
    apply_effect         — transform text with a named effect
    ALL_EFFECT_NAMES     — frozenset of every valid effect/alias name
    EFFECT_NAMES_SORTED  — sorted list for prompt injection
"""

from .manager import ConeManager
from .registry import apply_effect, ALL_EFFECT_NAMES, EFFECT_NAMES_SORTED

__all__ = ["ConeManager", "apply_effect", "ALL_EFFECT_NAMES", "EFFECT_NAMES_SORTED"]
