"""Lexical-only BM25F baseline using exactly the indexed base symbols."""

from collections.abc import Sequence

from smriti.lexical.index import BM25Index, SearchHit
from smriti.models import Symbol


class LexicalBaseline:
    def __init__(self, symbols: Sequence[Symbol]) -> None:
        self.index = BM25Index()
        for symbol in symbols:
            if symbol.path == '<external>' or not symbol.body:
                continue
            self.index.add(
                symbol.id,
                {'signature': symbol.signature, 'docstring': symbol.docstring, 'body': symbol.body},
            )

    def search(self, query: str, k: int = 50) -> list[SearchHit]:
        return self.index.search(query, k)
