"""Independent structural oracle and ambiguity-safe rename evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Label:
    symbol_id: str
    content_hash: str
    expected: str
    reason: str


def identical_renames(previous: Mapping[str, str], current: Mapping[str, str]) -> dict[str, str]:
    removed: dict[str, list[str]] = defaultdict(list)
    added: dict[str, list[str]] = defaultdict(list)
    for identity in previous.keys() - current.keys():
        removed[previous[identity]].append(identity)
    for identity in current.keys() - previous.keys():
        added[current[identity]].append(identity)
    return {
        old[0]: added[digest][0]
        for digest, old in removed.items()
        if digest and len(old) == 1 and len(added.get(digest, [])) == 1
    }


def label(
    symbol_id: str,
    baseline_hash: str,
    current: Mapping[str, str],
    renames: Mapping[str, str],
) -> Label:
    identity = renames.get(symbol_id, symbol_id)
    if identity not in current:
        return Label(identity, baseline_hash, 'orphaned', 'symbol_missing')
    if current[identity] != baseline_hash:
        return Label(identity, baseline_hash, 'stale', 'implementation_changed')
    return Label(identity, baseline_hash, 'fresh', 'identical_implementation')
