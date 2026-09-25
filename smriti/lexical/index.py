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
        self.remove(id)
        self.documents[id] = {field: Counter(code_tokens(text)) for field,text in fields.items()}
        self._rebuild()

    def _rebuild(self):
        self.postings = {}
        for id, fields in self.documents.items():
            for field, counts in fields.items():
                for term, count in counts.items():
                    self.postings.setdefault(term, {}).setdefault(id, {})[field] = count

    @property
    def document_frequency(self):
        return {term:len(postings) for term,postings in self.postings.items()}

    @property
    def lengths(self):
        return {id:{field:sum(counts.values()) for field,counts in fields.items()} for id,fields in self.documents.items()}

    @property
    def averages(self):
        fields = {f for doc in self.documents.values() for f in doc}
        return {f:sum(doc.get(f,0) for doc in self.lengths.values()) / max(1,len(self.documents)) for f in fields}


def bm25_score(tf, df, count, length, average, k1=1.2, b=0.75):
    import math
    if not tf or not average: return 0.0
    idf=math.log(1+(count-df+0.5)/(df+0.5))
    return idf*tf*(k1+1)/(tf+k1*(1-b+b*length/average))

def _search(self, query, k=20):
    import math
    if k < 0: raise ValueError("k must be nonnegative")
    scores = {}
    averages, lengths = self.averages, self.lengths
    for term in set(code_tokens(query)):
        posting = self.postings.get(term, {})
        idf=math.log(1+(len(self.documents)-len(posting)+0.5)/(len(posting)+0.5))
        for id, fields in posting.items():
            tf=sum(self.weights.get(f,1)*count/(1-self.b+self.b*lengths[id][f]/(averages[f] or 1)) for f,count in fields.items())
            scores[id]=scores.get(id,0)+idf*tf*(self.k1+1)/(tf+self.k1)
    return [SearchHit(id,score) for id,score in sorted(scores.items(), key=lambda item:(-item[1],item[0]))[:k]]

BM25Index.search = _search


def _remove(self, id):
    self.documents.pop(id,None)
    self._rebuild()

BM25Index.remove = _remove
