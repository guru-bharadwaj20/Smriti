import random

from smriti.vector.hnsw import HNSWIndex
from smriti.vector.math import exact_search


def test_update():
    x = HNSWIndex()
    x.add('a', [1, 0])
    x.add('b', [0, 1])
    x.add('a', [-1, 0])
    assert x.search([1, 0], 1)[0].id == 'b'


def test_exact_oracle_recall():
    r = random.Random(47)
    vectors = {str(i): [r.gauss(0, 1) for _ in range(8)] for i in range(120)}
    x = HNSWIndex(m=12, ef_search=120)
    for id, v in vectors.items():
        x.add(id, v)
    overlaps = []
    for query in list(vectors.values())[:20]:
        truth = {h.id for h in exact_search(vectors, query, 10)}
        found = {h.id for h in x.search(query, 10)}
        overlaps.append(len(truth & found) / 10)
    assert sum(overlaps) / len(overlaps) >= 0.95
    assert x.validate()
