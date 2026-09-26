"""One-component ablations of the actual production retrieval pipeline."""

from copy import copy
from dataclasses import replace
from unittest.mock import patch

from smriti.pack.packer import greedy
from smriti.server.retrieval import Retriever


def variant(retriever: Retriever, name: str) -> Retriever:
    result = copy(retriever)
    result._reasons = {}
    if name == 'no_vector':
        result.vector = None
    elif name == 'no_graph':
        result.snapshot = replace(result.snapshot, edges=())
    elif name not in {'full', 'greedy'}:
        raise ValueError(f'Unknown ablation: {name}')
    return result


def context(retriever: Retriever, name: str, query: str, budget: int):
    engine = variant(retriever, name)
    if name == 'greedy':
        # Keep production representations, dependencies, explanation rendering,
        # deduplication and final tokenizer recount identical to the full pipeline.
        with patch(
            'smriti.pack.packer.knapsack', lambda groups, budget, bucket=1: greedy(groups, budget)
        ):
            return engine.context(query, budget)
    return engine.context(query, budget)
