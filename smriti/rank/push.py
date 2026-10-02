"""Residual push Personalized PageRank with an explicit remaining-mass bound."""

import heapq
import math
from dataclasses import dataclass

from smriti.rank.pagerank import Graph


@dataclass(frozen=True)
class PushResult:
    scores: dict[str, float]
    pushes: int
    residual_l1: float
    converged: bool


def push_pagerank(
    graph: Graph,
    seeds: dict[str, float],
    damping: float = 0.85,
    tolerance: float = 1e-6,
    max_pushes: int = 1_000_000,
) -> PushResult:
    if not 0 <= damping < 1 or tolerance <= 0 or not math.isfinite(tolerance) or max_pushes < 1:
        raise ValueError('Invalid push PageRank configuration')
    if any(node not in graph for node in seeds):
        raise ValueError('Seed absent from graph')
    if any(not math.isfinite(value) or value < 0 for value in seeds.values()):
        raise ValueError('Seed weights must be finite and nonnegative')
    for neighbors in graph.values():
        if any(
            node not in graph or not math.isfinite(value) or value < 0
            for node, value in neighbors.items()
        ):
            raise ValueError('Invalid graph transition')
    total = sum(seeds.values())
    if not total:
        return PushResult({}, 0, 0, True)
    teleport = {node: value / total for node, value in seeds.items() if value}
    residual = dict(teleport)
    settled: dict[str, float] = {}
    queue = [(-value, node) for node, value in residual.items()]
    heapq.heapify(queue)
    remaining = 1.0
    pushes = 0
    while queue and remaining > tolerance and pushes < max_pushes:
        negative, node = heapq.heappop(queue)
        mass = residual.get(node, 0)
        if mass == 0 or negative != -mass:
            continue
        residual[node] = 0
        settled[node] = settled.get(node, 0) + (1 - damping) * mass
        remaining -= (1 - damping) * mass
        neighbors = graph[node]
        weight = sum(neighbors.values())
        transitions = (
            {target: value / weight for target, value in neighbors.items()} if weight else teleport
        )
        for target, probability in transitions.items():
            if probability:
                residual[target] = residual.get(target, 0) + damping * mass * probability
                heapq.heappush(queue, (-residual[target], target))
        pushes += 1
    # Do not renormalize: omitted residual is the L1 error bound for nonnegative transitions.
    return PushResult(
        dict(sorted(settled.items(), key=lambda item: (-item[1], item[0]))),
        pushes,
        max(0, sum(residual.values())),
        remaining <= tolerance,
    )
