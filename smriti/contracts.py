"""Public retrieval output contracts shared by interfaces."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHit:
    id: str
    score: float
    reason: str = ''


@dataclass(frozen=True)
class ContextItem:
    symbol_id: str
    path: str
    level: int
    reason: str


@dataclass(frozen=True)
class ContextResponse:
    text: str
    token_count: int
    budget: int
    tokenizer: str
    index_version: int
    items: tuple[ContextItem, ...] = ()

    def __post_init__(self) -> None:
        if self.budget < 0 or not 0 <= self.token_count <= self.budget:
            raise ValueError('Context exceeds its token budget')
