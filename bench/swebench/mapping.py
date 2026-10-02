"""Map changed fix lines to symbols from the task's base commit."""

from collections.abc import Sequence

from bench.swebench.ground_truth import ChangedFile
from smriti.models import Symbol


def gold_base_functions(changes: Sequence[ChangedFile], symbols: Sequence[Symbol]) -> set[str]:
    """Prefer the innermost function at each changed base line."""
    gold: set[str] = set()
    for change in changes:
        if change.old_path is None:
            continue
        candidates = [
            symbol
            for symbol in symbols
            if symbol.path == change.old_path and symbol.kind in {'function', 'method'}
        ]
        for line in (*change.removed_lines, *change.added_at_base_lines):
            enclosing = [
                symbol for symbol in candidates if symbol.start_line <= line <= symbol.end_line
            ]
            if enclosing:
                innermost = min(
                    enclosing, key=lambda symbol: (symbol.end_line - symbol.start_line, symbol.id)
                )
                gold.add(innermost.id)
    return gold
