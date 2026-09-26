"""Coverage metrics for packed source, including full-parent descendants."""

from collections.abc import Mapping, Sequence

from smriti.models import Symbol
from smriti.pack.packer import ContextPacker, PackedContext


def packed_recall(context: PackedContext, gold_ids: set[str]) -> float | None:
    if not gold_ids:
        return None
    exposed = set(context.covered_ids or [item.id for item in context.items])
    return len(exposed & gold_ids) / len(gold_ids)


def recall_at_budget(
    symbols: Sequence[Symbol],
    scores: Mapping[str, float],
    gold_ids: set[str],
    budget: int,
    packer: ContextPacker | None = None,
) -> dict[str, float | int | None]:
    packer = packer or ContextPacker()
    result = packer.pack(symbols, scores, budget)
    return {
        'budget': budget,
        'tokens': result.token_count,
        'function_recall': packed_recall(result, gold_ids),
    }
