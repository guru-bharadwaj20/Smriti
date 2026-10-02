"""Confusion matrices with explicit undefined-denominator reporting."""

from __future__ import annotations

from collections.abc import Iterable


def stale_metrics(rows: Iterable[dict[str, object]]) -> dict[str, int | float | None]:
    tp = fp = tn = fn = 0
    for row in rows:
        expected = row['expected'] != 'fresh'
        observed = row['observed'] != 'fresh'
        if expected and observed:
            tp += 1
        elif observed:
            fp += 1
        elif expected:
            fn += 1
        else:
            tn += 1
    return {
        'true_positive': tp,
        'false_positive': fp,
        'true_negative': tn,
        'false_negative': fn,
        'precision': tp / (tp + fp) if tp + fp else None,
        'recall': tp / (tp + fn) if tp + fn else None,
        'observations': tp + fp + tn + fn,
    }
