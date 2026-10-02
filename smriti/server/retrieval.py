"""Snapshot-bound hybrid retrieval and fully counted context rendering."""

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from smriti.contracts import ContextItem, ContextResponse
from smriti.lexical.index import BM25Index
from smriti.pack.packer import ContextPacker, covered_symbols
from smriti.pack.tokens import TokenCounter
from smriti.rank.hybrid import reciprocal_rank_fusion
from smriti.rank.pagerank import adjacency, personalized_pagerank
from smriti.server.snapshots import IndexSnapshot
from smriti.vector.embedding import BatchedEmbedder, EmbeddingCache, Encoder, ONNXEmbedder
from smriti.vector.hnsw import HNSWIndex

# Weight of personalized PageRank relative to normalized fused retrieval scores.
GRAPH_WEIGHT = 1.0


@dataclass(frozen=True)
class RankComponents:
    lexical: list[Any]
    vector: list[Any]
    fused: dict[str, float]
    propagated: dict[str, float]


class Retriever:
    def __init__(
        self,
        snapshot: IndexSnapshot,
        tokenizer: str = 'cl100k_base',
        model_dir: Path | None = None,
        state_dir: Path | None = None,
        encoder: Encoder | None = None,
    ) -> None:
        self.snapshot = snapshot
        self.graph_weight = GRAPH_WEIGHT
        self.symbols = {s.id: s for s in snapshot.symbols if s.path != '<external>'}
        self.counter = TokenCounter(tokenizer)
        self.encoder = encoder
        if self.encoder is None and model_dir is not None:
            self.encoder = BatchedEmbedder(
                ONNXEmbedder(model_dir / 'model.onnx', model_dir / 'tokenizer.json')
            )
        self.lexical = BM25Index()
        self.vector: HNSWIndex | None = None
        model_version = self.encoder.version if self.encoder is not None else 'lexical-only'
        key = sha256((model_version + '\0' + tokenizer).encode()).hexdigest()[:16]
        cache = (
            state_dir / 'retrieval' / f'{snapshot.version}-{key}' if state_dir is not None else None
        )
        if cache is not None and (cache / 'complete.json').exists():
            self.lexical = BM25Index.load(cache / 'lexical.json')
            if self.encoder is not None:
                self.vector = HNSWIndex.load(cache / 'hnsw.json')
        else:
            for symbol in self.symbols.values():
                self.lexical.add(
                    symbol.id,
                    {
                        'signature': symbol.qualname + ' ' + symbol.signature,
                        'docstring': symbol.docstring,
                        'body': symbol.body,
                    },
                )
            if self.encoder is not None:
                self.vector = HNSWIndex()
                source = list(self.symbols.values())
                texts = [s.qualname + '\n' + s.signature + '\n' + s.body for s in source]
                if state_dir is not None:
                    state_dir.mkdir(parents=True, exist_ok=True)
                    embeddings = EmbeddingCache(state_dir / 'embeddings.sqlite', self.encoder)
                    try:
                        vectors = embeddings.embed(texts)
                    finally:
                        embeddings.close()
                else:
                    vectors = self.encoder.embed(texts)
                for symbol, vector in zip(source, vectors, strict=True):
                    self.vector.add(symbol.id, vector)
            if cache is not None:
                cache.parent.mkdir(parents=True, exist_ok=True)
                build = cache.parent / ('.build-' + uuid.uuid4().hex)
                build.mkdir()
                self.lexical.save(build / 'lexical.json')
                if self.vector is not None:
                    self.vector.save(build / 'hnsw.json')
                (build / 'complete.json').write_text(
                    json.dumps({'version': snapshot.version, 'model': model_version}),
                    encoding='utf-8',
                )
                try:
                    os.rename(build, cache)
                except OSError:
                    if not (cache / 'complete.json').exists():
                        raise
                    # Another complete builder won. Remove only our own private
                    # directory, whose resolved path stays under the cache root.
                    if not build.resolve().is_relative_to(cache.parent.resolve()):
                        raise ValueError('Cache cleanup escaped its state directory') from None
                    shutil.rmtree(build)
        self._reasons: dict[str, str] = {}

    def components(self, task: str) -> RankComponents:
        """Candidate lists and graph scores before they are combined."""
        lexical = self.lexical.search(task, 50)
        vector = (
            self.vector.search(self.encoder.embed([task])[0], 50)
            if self.vector is not None and self.encoder is not None
            else []
        )
        fused = reciprocal_rank_fusion([lexical, vector])
        if not fused:
            return RankComponents(lexical, vector, {}, {})
        edges = [
            (e.source, e.target, e.kind, e.confidence)
            for e in self.snapshot.edges
            if e.source in self.symbols and e.target in self.symbols
        ]
        # Calls remain directed in storage; reverse ranking transitions reach
        # callers and enclosing classes without changing the canonical graph.
        ranking_edges = [
            *edges,
            *(
                (target, source, kind, confidence * 0.5)
                for source, target, kind, confidence in edges
            ),
        ]
        propagated = personalized_pagerank(adjacency(self.symbols, ranking_edges), fused)
        return RankComponents(lexical, vector, fused, propagated)

    def combine(self, parts: RankComponents, graph_weight: float | None = None) -> dict[str, float]:
        weight = self.graph_weight if graph_weight is None else graph_weight
        if not parts.fused:
            return {}
        total = sum(parts.fused.values())
        scores = {
            identity: parts.fused.get(identity, 0) / total
            + weight * parts.propagated.get(identity, 0)
            for identity in self.symbols
        }
        return dict(sorted(scores.items(), key=lambda item: (-item[1], item[0])))

    def rank(self, task: str) -> dict[str, float]:
        parts = self.components(task)
        scores = self.combine(parts)
        lexical_ids = {hit.id for hit in parts.lexical}
        vector_ids = {hit.id for hit in parts.vector}
        self._reasons = {
            identity: ', '.join(
                reason
                for reason, present in [
                    ('identifier match', identity in lexical_ids),
                    ('semantic match', identity in vector_ids),
                    ('code graph', parts.propagated.get(identity, 0) > 0),
                ]
                if present
            )
            for identity in scores
        }
        return scores

    def context(self, task: str, budget: int, preamble: str = '') -> ContextResponse:
        scores = self.rank(task)
        candidates = set(list(scores)[:64])
        for identity in tuple(candidates):
            parent = self.symbols[identity].parent_id
            while parent is not None and parent in self.symbols:
                candidates.add(parent)
                parent = self.symbols[parent].parent_id
        source = [self.symbols[identity] for identity in sorted(candidates)]
        if self.counter.count(preamble) > budget:
            preamble = ''
        packed = ContextPacker(self.counter).pack(
            source, scores, budget, memory_tokens=self.counter.count(preamble)
        )
        selected = list(packed.items)

        def render() -> str:
            return preamble + ''.join(
                f'# Why: {self._reasons.get(option.id, "required parent")}\n' + option.text
                for option in selected
            )

        text = render()
        while self.counter.count(text) > budget and selected:
            selected.pop(
                min(
                    range(len(selected)),
                    key=lambda i: (selected[i].value / max(1, selected[i].cost), selected[i].id),
                )
            )
            text = render()
        items = tuple(
            ContextItem(
                option.id,
                self.symbols[option.id].path,
                {'name': 1, 'signature': 2, 'body': 3}[option.level],
                self._reasons.get(option.id, 'required parent'),
            )
            for option in selected
        )
        return ContextResponse(
            text,
            self.counter.count(text),
            budget,
            self.counter.encoding_name,
            self.snapshot.version,
            items,
            tuple(sorted(covered_symbols(selected, source))),
        )
