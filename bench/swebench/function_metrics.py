"""Symbol-location metrics evaluated independently of retriever training."""

from collections.abc import Sequence


def function_recall_at_k(ranked_ids: Sequence[str], gold_ids: set[str], k: int) -> float | None:
    if k < 0:
        raise ValueError('k cannot be negative')
    if not gold_ids:
        return None
    selected = list(dict.fromkeys(ranked_ids))[:k]
    return len(set(selected) & gold_ids) / len(gold_ids)
