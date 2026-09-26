"""Aider-style identifier/graph repo-map baseline; not official Aider output."""

from collections.abc import Sequence

from smriti.lexical.index import SearchHit
from smriti.lexical.tokenizer import code_tokens
from smriti.models import Edge, Symbol
from smriti.rank.pagerank import adjacency, personalized_pagerank


def repo_map_baseline(
    symbols: Sequence[Symbol], edges: Sequence[Edge], query: str, k: int = 50
) -> list[SearchHit]:
    if k < 0:
        raise ValueError('k must be nonnegative')
    selected = [symbol for symbol in symbols if symbol.path != '<external>' and symbol.body]
    words = set(code_tokens(query))
    seeds = {
        symbol.id: float(len(words & set(code_tokens(symbol.qualname)))) for symbol in selected
    }
    ids = {symbol.id for symbol in selected}
    graph = adjacency(ids, [edge for edge in edges if edge.source in ids and edge.target in ids])
    scores = personalized_pagerank(graph, seeds)
    return sorted(
        [SearchHit(id, score) for id, score in scores.items()], key=lambda hit: (-hit.score, hit.id)
    )[:k]
