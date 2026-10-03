"""From-scratch hierarchical navigable small-world index, cosine metric."""

from __future__ import annotations

import heapq
import json
import math
import random
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .math import VectorHit, distance, native_store, normalize


class HNSWIndex:
    def __init__(
        self, m: int = 16, ef_construction: int = 100, ef_search: int = 50, seed: int = 0
    ) -> None:
        if m < 2 or ef_construction < m or ef_search < 1:
            raise ValueError('invalid HNSW configuration')
        self.m = m
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.seed = seed
        self.random = random.Random(seed)
        self.vectors: dict[str, tuple[float, ...]] = {}
        self.levels: dict[str, int] = {}
        self.graph: dict[str, dict[int, set[str]]] = {}
        self.entry: str | None = None
        self.deleted: set[str] = set()
        self._reset_store()

    def _reset_store(self) -> None:
        # Stored nodes are compared by slot in the optional Rust store; results
        # are bit-identical to distance() on the stored tuples.
        self._store: Any = native_store()
        self._slots: dict[str, int] = {}

    def _pair(self, left: str, right: str) -> float:
        if self._store is None:
            return distance(self.vectors[left], self.vectors[right])
        for id in (left, right):
            if id not in self._slots:
                self._slots[id] = self._store.push(list(self.vectors[id]))
        return float(self._store.distance(self._slots[left], self._slots[right]))

    def _to_query(self, query: Sequence[float]) -> Callable[[str], float]:
        return lambda id: distance(query, self.vectors[id])

    def _to_node(self, node: str) -> Callable[[str], float]:
        return lambda id: self._pair(node, id)

    def random_level(self) -> int:
        return min(32, int(-math.log(max(self.random.random(), 1e-15)) / math.log(self.m)))

    def _refresh_entry(self) -> None:
        self.entry = (
            min(self.levels, key=lambda id: (-self.levels[id], id)) if self.levels else None
        )

    def _greedy(self, dist: Callable[[str], float], entry: str, layer: int) -> str:
        best = entry
        best_dist = dist(best)
        while True:
            candidate = min(
                [best, *self.graph[best].get(layer, ())],
                key=lambda id: (dist(id), id),
            )
            value = dist(candidate)
            if value >= best_dist:
                return best
            best, best_dist = candidate, value

    def _layer_search(
        self, dist: Callable[[str], float], entries: Sequence[str], ef: int, layer: int
    ) -> list[tuple[float, str]]:
        visited = set(entries)
        candidates = [(dist(id), id) for id in entries]
        heapq.heapify(candidates)
        best = [(-d, id) for d, id in candidates]
        heapq.heapify(best)
        while candidates:
            d, id = heapq.heappop(candidates)
            if len(best) >= ef and d > -best[0][0]:
                break
            for neighbor in sorted(self.graph[id].get(layer, ())):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                nd = dist(neighbor)
                if len(best) < ef or nd < -best[0][0]:
                    heapq.heappush(candidates, (nd, neighbor))
                    heapq.heappush(best, (-nd, neighbor))
                    if len(best) > ef:
                        heapq.heappop(best)
        return sorted([(-d, id) for d, id in best])

    def _select(self, candidates: Sequence[tuple[float, str]], limit: int) -> list[str]:
        selected: list[str] = []
        rejected: list[str] = []
        for d, id in sorted(candidates):
            if all(self._pair(id, other) >= d for other in selected):
                selected.append(id)
            else:
                rejected.append(id)
            if len(selected) == limit:
                return selected
        return (selected + rejected)[:limit]

    def add(self, id: str, vector: Sequence[float]) -> None:
        value = normalize(vector)
        if self.vectors and len(value) != len(next(iter(self.vectors.values()))):
            raise ValueError('dimension mismatch')
        if id in self.vectors:
            self.vectors[id] = value
            self._slots.pop(id, None)
            self.deleted.discard(id)
            self.rebuild()
            return
        level = self.random_level()
        self.vectors[id] = value
        self.levels[id] = level
        self.graph[id] = {layer: set() for layer in range(level + 1)}
        if self.entry is None:
            self.entry = id
            return
        entry = self.entry
        max_level = self.levels[entry]
        dist = self._to_node(id)
        for layer in range(max_level, level, -1):
            entry = self._greedy(dist, entry, layer)
        for layer in range(min(level, max_level), -1, -1):
            candidates = self._layer_search(dist, [entry], self.ef_construction, layer)
            neighbors = self._select(candidates, self.m)
            for other in neighbors:
                self.graph[id][layer].add(other)
                self.graph[other][layer].add(id)
            for other in [id, *neighbors]:
                limit = self.m * 2 if layer == 0 else self.m
                links = self.graph[other][layer]
                if len(links) > limit:
                    keep = set(self._select([(self._pair(other, n), n) for n in links], limit))
                    for removed in links - keep:
                        self.graph[removed][layer].discard(other)
                    self.graph[other][layer] = keep
            if candidates:
                entry = candidates[0][1]
        if level > max_level:
            self.entry = id

    def search(self, query: Sequence[float], k: int = 10, ef: int | None = None) -> list[VectorHit]:
        if k < 0:
            raise ValueError('k must be nonnegative')
        if not self.entry or not k:
            return []
        dist = self._to_query(normalize(query))
        entry = self.entry
        for layer in range(self.levels[entry], 0, -1):
            entry = self._greedy(dist, entry, layer)
        candidates = self._layer_search(dist, [entry], max(k, ef or self.ef_search), 0)
        return [VectorHit(id, 1 - d) for d, id in candidates if id not in self.deleted][:k]

    def remove(self, id: str) -> None:
        if id in self.vectors:
            self.deleted.add(id)

    def rebuild(self) -> None:
        live = {id: v for id, v in self.vectors.items() if id not in self.deleted}
        self.vectors = {}
        self.levels = {}
        self.graph = {}
        self.entry = None
        self.deleted = set()
        self._reset_store()
        self.random = random.Random(self.seed)
        for id in sorted(live):
            self.add(id, live[id])

    def save(self, path: str | Path) -> None:
        data = {
            'version': 1,
            'm': self.m,
            'ef_construction': self.ef_construction,
            'ef_search': self.ef_search,
            'seed': self.seed,
            'vectors': self.vectors,
            'levels': self.levels,
            'entry': self.entry,
            'deleted': sorted(self.deleted),
            'graph': {
                id: {str(layer): sorted(links) for layer, links in layers.items()}
                for id, layers in self.graph.items()
            },
            'random_state': self.random.getstate(),
        }
        Path(path).write_text(json.dumps(data, sort_keys=True), encoding='utf-8')

    @classmethod
    def load(cls, path: str | Path) -> HNSWIndex:
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding='utf-8'))
        if data['version'] != 1:
            raise ValueError('unsupported graph format')
        x = cls(data['m'], data['ef_construction'], data['ef_search'], data['seed'])
        x.vectors = {id: tuple(v) for id, v in data['vectors'].items()}
        x.levels = data['levels']
        x.entry = data['entry']
        x.deleted = set(data['deleted'])
        x.graph = {
            id: {int(layer): set(links) for layer, links in layers.items()}
            for id, layers in data['graph'].items()
        }
        state = data['random_state']
        x.random.setstate((state[0], tuple(state[1]), state[2]))
        return x

    def validate(self) -> bool:
        if set(self.vectors) != set(self.graph) or set(self.graph) != set(self.levels):
            raise ValueError('node sets differ')
        if self.entry is not None and self.levels[self.entry] != max(self.levels.values()):
            raise ValueError('invalid entry level')
        for id, layers in self.graph.items():
            if set(layers) != set(range(self.levels[id] + 1)):
                raise ValueError('missing layers')
            for layer, links in layers.items():
                if len(links) > (2 * self.m if layer == 0 else self.m):
                    raise ValueError('degree exceeded')
                for other in links:
                    if (
                        other == id
                        or other not in self.graph
                        or layer not in self.graph[other]
                        or id not in self.graph[other][layer]
                    ):
                        raise ValueError('invalid reciprocal edge')
        return True
