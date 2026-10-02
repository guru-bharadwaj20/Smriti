"""Dependency-free cosine distance and exhaustive nearest-neighbor oracle."""

import math
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float


def normalize(vector: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(x) for x in vector)
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError('finite nonempty vector required')
    norm = math.sqrt(sum(x * x for x in values))
    if not norm:
        raise ValueError('zero vector has no cosine direction')
    return tuple(x / norm for x in values)


def python_distance(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError('dimension mismatch')
    return max(0.0, min(2.0, 1 - sum(x * y for x, y in zip(a, b, strict=True))))


def _select_distance() -> Callable[[Sequence[float], Sequence[float]], float]:
    """Use the optional Rust kernel when installed; SMRITI_NATIVE=0 disables it.

    The kernel performs the same left-to-right f64 accumulation, so seeded HNSW
    graphs and query results are identical (bench/vector/native_profile.json).
    """
    if os.environ.get('SMRITI_NATIVE', '1') == '0':
        return python_distance
    try:
        import smriti_native  # type: ignore[import-not-found, import-untyped, unused-ignore]
    except ImportError:
        return python_distance
    return cast(Callable[[Sequence[float], Sequence[float]], float], smriti_native.distance)


distance = _select_distance()
NATIVE = distance is not python_distance


def exact_search(
    vectors: Mapping[str, Sequence[float]],
    query: Sequence[float],
    k: int = 10,
    excluded: Iterable[str] = (),
) -> list[VectorHit]:
    query = normalize(query)
    excluded = set(excluded)
    hits = [
        VectorHit(id, 1 - distance(query, normalize(v)))
        for id, v in vectors.items()
        if id not in excluded
    ]
    return sorted(hits, key=lambda h: (-h.score, h.id))[:k]
