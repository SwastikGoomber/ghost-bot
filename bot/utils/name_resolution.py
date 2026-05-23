"""
Shared name/alias helpers.

Feature modules can exchange NameAliasMap without importing each other's
managers or storage internals.
"""

from __future__ import annotations

from collections.abc import Iterable

from bot.utils.models import NameAliasMap, UserState


def _normalise_name(name: str) -> str:
    return " ".join(name.lower().split())


def _identity_names(state: UserState) -> set[str]:
    names: set[str] = set()
    for identity in state.identifiers.values():
        for field in (identity.username, identity.nickname, identity.display_name):
            if field and field.strip():
                names.add(field.strip())
    return names


def build_name_alias_map(states: Iterable[UserState]) -> NameAliasMap:
    """
    Build a lookup where every known spelling for a user expands to all others.

    This is intentionally storage-agnostic: callers decide which UserState
    objects are in scope, and consumers only receive a typed alias map.
    """
    aliases_by_name: dict[str, list[str]] = {}
    seen_states: set[int] = set()

    for state in states:
        if id(state) in seen_states:
            continue
        seen_states.add(id(state))

        names = _identity_names(state)
        names.update(n.strip() for n in state.name_variants if n and n.strip())
        names.update(a.strip() for a in state.aliases if a and a.strip())
        if state.primary_name and state.primary_name.strip():
            names.add(state.primary_name.strip())

        clean_names = sorted(names, key=lambda n: n.lower())
        if not clean_names:
            continue

        for name in clean_names:
            aliases_by_name[_normalise_name(name)] = clean_names

    return NameAliasMap(aliases_by_name=aliases_by_name)
