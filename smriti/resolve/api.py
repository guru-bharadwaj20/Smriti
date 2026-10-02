"""Declared API boundaries linking consumers and providers across languages."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from smriti.models import Edge, Symbol


@dataclass(frozen=True)
class ApiBinding:
    symbol_id: str
    protocol: str
    endpoint: str
    role: Literal['consumer', 'provider']

    def __post_init__(self) -> None:
        if not self.symbol_id or not self.protocol or not self.endpoint:
            raise ValueError('API bindings require symbol, protocol and endpoint')
        if self.role not in {'consumer', 'provider'}:
            raise ValueError('Unknown API binding role')


def cross_language_edges(symbols: list[Symbol], bindings: list[ApiBinding]) -> list[Edge]:
    """Use explicit protocol/endpoint declarations; never infer an RPC from a name."""
    by_id = {symbol.id: symbol for symbol in symbols}
    languages = {
        '.py': 'python',
        '.go': 'go',
        '.java': 'java',
        '.ts': 'typescript',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.hpp': 'cpp',
    }
    for binding in bindings:
        if binding.symbol_id not in by_id:
            raise ValueError(f'API anchor does not exist: {binding.symbol_id}')
    edges: list[Edge] = []
    for consumer in bindings:
        if consumer.role != 'consumer':
            continue
        consumer_language = languages.get(PurePosixPath(by_id[consumer.symbol_id].path).suffix)
        if consumer_language is None:
            continue
        providers = {
            binding.symbol_id
            for binding in bindings
            if binding.role == 'provider'
            and (binding.protocol, binding.endpoint) == (consumer.protocol, consumer.endpoint)
            and languages.get(PurePosixPath(by_id[binding.symbol_id].path).suffix)
            not in {None, consumer_language}
        }
        edges.extend(
            Edge(
                consumer.symbol_id,
                provider,
                'calls' if len(providers) == 1 else 'may_call',
                0.8 if len(providers) == 1 else 0.25,
            )
            for provider in providers
        )
    return sorted(set(edges), key=lambda edge: (edge.source, edge.target))
