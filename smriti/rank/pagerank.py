"""Sparse confidence-weighted personalized PageRank."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import TypeAlias

from smriti.models import Edge

Graph: TypeAlias = dict[str, dict[str, float]]
EdgeTuple: TypeAlias = tuple[str, str, str] | tuple[str, str, str, float]
EDGE_WEIGHTS = {
    'calls': 1.0,
    'imports': 0.5,
    'contains': 0.3,
    'defines': 0.3,
    'inherits': 0.7,
    'tests': 1.0,
    'config': 0.6,
    'may_call': 0.3,
}


def edge_parts(edge: Edge | EdgeTuple) -> tuple[str, str, str, float]:
    if isinstance(edge, Edge):
        return edge.source, edge.target, edge.kind, edge.confidence
    return edge[0], edge[1], edge[2], edge[3] if len(edge) == 4 else 1.0


def edge_weight(kind: str, confidence: float = 1.0) -> float:
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError('confidence outside [0,1]')
    return EDGE_WEIGHTS.get(kind, 0.1) * confidence


def adjacency(nodes: Iterable[str], edges: Iterable[Edge | EdgeTuple]) -> Graph:
    result: Graph = {id: {} for id in nodes}
    for edge in edges:
        source, target, kind, confidence = edge_parts(edge)
        weight = edge_weight(kind, confidence)
        if source not in result or target not in result:
            continue
        if weight > 0:
            result[source][target] = result[source].get(target, 0) + weight
    return result


def transitions(graph: Graph) -> Graph:
    result: Graph = {}
    for node, links in graph.items():
        if any(target not in graph for target in links):
            raise ValueError('transition target missing')
        if any(not math.isfinite(w) or w < 0 for w in links.values()):
            raise ValueError('invalid graph weight')
        positive = {target: weight for target, weight in links.items() if weight > 0}
        total = sum(positive.values())
        result[node] = (
            {target: weight / total for target, weight in positive.items()} if total else {}
        )
    return result


def restart_distribution(nodes: Iterable[str], seeds: Mapping[str, float]) -> dict[str, float]:
    nodes = list(nodes)
    if any(not math.isfinite(value) or value < 0 for value in seeds.values()):
        raise ValueError('invalid restart seed')
    values = {id: seeds.get(id, 0.0) for id in nodes}
    total = sum(values.values())
    return {id: value / total if total else 1 / len(nodes) for id, value in values.items()}


def personalized_pagerank(
    graph: Graph,
    seeds: Mapping[str, float],
    damping: float = 0.85,
    tolerance: float = 1e-10,
    max_iterations: int = 200,
) -> dict[str, float]:
    if (
        not math.isfinite(damping)
        or not 0 <= damping < 1
        or not math.isfinite(tolerance)
        or tolerance <= 0
        or max_iterations < 1
    ):
        raise ValueError('invalid convergence settings')
    if not graph:
        return {}
    restart = restart_distribution(graph, seeds)
    scores = restart.copy()
    matrix = transitions(graph)
    for _ in range(max_iterations):
        dangling = sum(scores[id] for id, links in matrix.items() if not links)
        updated = {
            id: (1 - damping) * restart[id] + damping * dangling * restart[id] for id in graph
        }
        for source, links in matrix.items():
            for target, weight in links.items():
                updated[target] += damping * scores[source] * weight
        delta = sum(abs(updated[id] - scores[id]) for id in graph)
        scores = updated
        if delta < tolerance:
            break
    return dict(sorted(scores.items(), key=lambda item: (-item[1], item[0])))
