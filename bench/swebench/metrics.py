"""Retrieval metrics; ground truth must be kept outside indexed source."""

from collections.abc import Sequence


def file_recall_at_k(ranked_paths: Sequence[str], gold_paths: set[str], k: int) -> float | None:
    """Unique-file recall; empty ground truth is undefined, never perfect recall."""
    if k < 0:
        raise ValueError('k cannot be negative')
    if not gold_paths:
        return None
    unique = list(dict.fromkeys(path.replace('\\', '/') for path in ranked_paths))
    gold = {path.replace('\\', '/') for path in gold_paths}
    return len(set(unique[:k]) & gold) / len(gold)
