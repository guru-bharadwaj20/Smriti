"""Deterministic query normalization, validated fusion, and graph expansion."""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol, TypedDict

from smriti.lexical.index import SearchHit
from smriti.models import Edge
from smriti.vector.math import VectorHit

from .pagerank import EdgeTuple, edge_parts


class Identified(Protocol):
    @property
    def id(self) -> str: ...


class LexicalSearch(Protocol):
    def search(self, query: str, k: int = 20) -> list[SearchHit]: ...


class VectorSearch(Protocol):
    def search(
        self, query: Sequence[float], k: int = 10, ef: int | None = None
    ) -> list[VectorHit]: ...


class Explanation(TypedDict):
    score: float
    lexical: bool
    vector: bool
    graph_score: float


def normalize_query(query: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', query).split()).casefold()


def lexical_candidates(index: LexicalSearch, query: str, k: int = 50) -> list[SearchHit]:
    return index.search(normalize_query(query), k)


def vector_candidates(
    index: VectorSearch, embed: Callable[[str], Sequence[float]], query: str, k: int = 50
) -> list[VectorHit]:
    return index.search(embed(normalize_query(query)), k)


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str | Identified]],
    weights: Sequence[float] | None = None,
    constant: float = 60,
) -> dict[str, float]:
    if not math.isfinite(constant) or constant <= 0:
        raise ValueError('positive fusion constant required')
    weights = [1.0] * len(rankings) if weights is None else weights
    if len(weights) != len(rankings) or any(not math.isfinite(w) or w < 0 for w in weights):
        raise ValueError('invalid fusion weights')
    scores: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        seen: set[str] = set()
        for position, hit in enumerate(ranking, 1):
            id = hit if isinstance(hit, str) else hit.id
            if id in seen:
                continue
            seen.add(id)
            scores[id] = scores.get(id, 0) + weight / (constant + position)
    return dict(sorted(scores.items(), key=lambda item: (-item[1], item[0])))


def expand_callers(seeds: Iterable[str], edges: Iterable[Edge | EdgeTuple]) -> set[str]:
    seeds = set(seeds)
    selected = set(seeds)
    for edge in edges:
        source, target, kind, _ = edge_parts(edge)
        if kind == 'calls' and target in seeds:
            selected.add(source)
    return selected


def expand_associations(seeds: Iterable[str], edges: Iterable[Edge | EdgeTuple]) -> set[str]:
    seeds = set(seeds)
    selected = set(seeds)
    for edge in edges:
        source, target, kind, _ = edge_parts(edge)
        if kind in {'tests', 'config'} and (source in seeds or target in seeds):
            selected.update([source, target])
    return selected


class RankingCache:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], dict[str, float]] = {}
        self.version: str | None = None

    def get(self, version: str, query: str) -> dict[str, float] | None:
        value = self.values.get((version, normalize_query(query)))
        return None if value is None else dict(value)

    def put(self, version: str, query: str, scores: Mapping[str, float]) -> None:
        self.values[(version, normalize_query(query))] = dict(scores)

    def invalidate(self, version: str) -> None:
        self.values = {key: value for key, value in self.values.items() if key[0] == version}
        self.version = version


def explain_candidates(
    scores: Mapping[str, float],
    lexical: Iterable[str | Identified] = (),
    vector: Iterable[str | Identified] = (),
    graph_scores: Mapping[str, float] | None = None,
) -> dict[str, Explanation]:
    lexical_ids = {hit if isinstance(hit, str) else hit.id for hit in lexical}
    vector_ids = {hit if isinstance(hit, str) else hit.id for hit in vector}
    return {
        id: {
            'score': score,
            'lexical': id in lexical_ids,
            'vector': id in vector_ids,
            'graph_score': (graph_scores or {}).get(id, 0),
        }
        for id, score in scores.items()
    }
