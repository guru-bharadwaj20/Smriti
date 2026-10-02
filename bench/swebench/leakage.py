"""Reject retrieval inputs that contain the fix patch or post-fix code."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from smriti.models import Symbol

MIN_LINE = 20


def added_lines(patch: str) -> dict[str, set[str]]:
    """Distinctive lines a patch introduces, keyed by the file it targets."""
    result: dict[str, set[str]] = {}
    path = None
    for line in patch.splitlines():
        if line.startswith('+++ '):
            target = line[4:].split('\t')[0]
            path = None if target == '/dev/null' else target.removeprefix('b/')
        elif path and line.startswith('+') and not line.startswith('+++'):
            text = line[1:].strip()
            if len(text) >= MIN_LINE:
                result.setdefault(path, set()).add(text)
    return result


def assert_no_leakage(
    query: str, patch: str, checkout: Path, symbols: Iterable[Symbol]
) -> dict[str, int]:
    """Raise when the query carries the diff or the index holds post-fix lines.

    A patch line already present in the base file (moved or duplicated code) is not
    evidence of leakage and is ignored.
    """
    if 'diff --git' in query or '\n+++ b/' in query:
        raise ValueError('Retrieval query contains patch text')
    bodies: dict[str, list[str]] = {}
    for symbol in symbols:
        bodies.setdefault(symbol.path, []).append(symbol.body)
    checked = 0
    for path, lines in added_lines(patch).items():
        base = checkout / path
        base_text = base.read_text(encoding='utf-8', errors='replace') if base.is_file() else ''
        indexed = '\n'.join(bodies.get(path, ()))
        for text in lines:
            if text in base_text:
                continue
            checked += 1
            if text in indexed:
                raise ValueError(f'Post-fix line from {path} is present in the index')
    return {'checked_post_fix_lines': checked}
