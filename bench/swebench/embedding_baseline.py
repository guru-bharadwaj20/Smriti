"""Embedding-only exhaustive cosine baseline, sharing optional content cache."""

from collections.abc import Sequence

import numpy as np

from smriti.lexical.index import SearchHit
from smriti.models import Symbol
from smriti.vector.embedding import Encoder
from smriti.vector.math import normalize


def embedding_text(symbol: Symbol) -> str:
    return (
        f'{symbol.path}\n{symbol.qualname}\n{symbol.signature}\n{symbol.docstring}\n{symbol.body}'
    )


class EmbeddingBaseline:
    def __init__(self, symbols: Sequence[Symbol], encoder: Encoder) -> None:
        self.encoder = encoder
        selected = [symbol for symbol in symbols if symbol.path != '<external>' and symbol.body]
        self.ids = [symbol.id for symbol in selected]
        self.vectors = np.asarray(
            encoder.embed([embedding_text(symbol) for symbol in selected]), dtype=np.float64
        )

    def search(self, query: str, k: int = 50) -> list[SearchHit]:
        if k < 0:
            raise ValueError('k must be nonnegative')
        if not self.ids or not k:
            return []
        query_vector = np.asarray(normalize(self.encoder.embed([query])[0]), dtype=np.float64)
        scores = self.vectors @ query_vector
        return sorted(
            [SearchHit(id, float(score)) for id, score in zip(self.ids, scores, strict=True)],
            key=lambda hit: (-hit.score, hit.id),
        )[:k]
