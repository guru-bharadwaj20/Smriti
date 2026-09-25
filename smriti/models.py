"""Shared, immutable source graph contracts."""

from dataclasses import dataclass
from typing import Literal

SymbolKind = Literal['module', 'class', 'function', 'method', 'variable']
EdgeKind = Literal['defines', 'contains', 'calls', 'imports', 'inherits', 'tests', 'may_call']


@dataclass(frozen=True)
class Symbol:
    id: str
    path: str
    name: str
    qualname: str
    kind: SymbolKind
    start_line: int = 1
    end_line: int = 1
    start_byte: int = 0
    end_byte: int = 0
    signature: str = ''
    docstring: str = ''
    body: str = ''
    content_hash: str = ''
    parent_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.path or not self.name:
            raise ValueError('Symbol identity, path and name are required')
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError('Invalid source line range')
        if self.start_byte < 0 or self.end_byte < self.start_byte:
            raise ValueError('Invalid source byte range')


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: EdgeKind
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.source or not self.target:
            raise ValueError('Edge endpoints are required')
        if not 0 <= self.confidence <= 1:
            raise ValueError('Edge confidence must be between zero and one')
