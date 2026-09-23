"""Mutable field-aware postings with exact recomputable statistics."""
from collections import Counter
from dataclasses import dataclass
from .tokenizer import code_tokens

@dataclass(frozen=True)
class SearchHit:
    id: str
    score: float

class BM25Index:
    def __init__(self, k1=1.2, b=0.75, weights=None):
        self.k1, self.b = k1, b
        self.weights = weights or {"signature":3.0,"docstring":2.0,"body":1.0}
        self.documents = {}
        self.postings = {}

    def add(self, id, fields):
        self.documents[id] = {field: Counter(code_tokens(text)) for field,text in fields.items()}
        self._rebuild()

    def _rebuild(self):
        self.postings = {}
        for id, fields in self.documents.items():
            for field, counts in fields.items():
                for term, count in counts.items():
                    self.postings.setdefault(term, {}).setdefault(id, {})[field] = count
