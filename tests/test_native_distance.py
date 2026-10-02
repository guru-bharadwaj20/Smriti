import random
from unittest.mock import patch

import pytest

from smriti.vector import math as vmath
from smriti.vector.hnsw import HNSWIndex


def test_native_kernel_builds_identical_graph_and_results() -> None:
    if not vmath.NATIVE:
        pytest.skip('optional smriti_native kernel not installed')
    rng = random.Random(3)
    vectors = [vmath.normalize([rng.gauss(0, 1) for _ in range(32)]) for _ in range(60)]

    def build() -> tuple[object, list[list[str]]]:
        index = HNSWIndex(seed=5)
        for number, vector in enumerate(vectors):
            index.add(str(number), vector)
        return index.graph, [[h.id for h in index.search(v, 5)] for v in vectors[:10]]

    native = build()
    with patch('smriti.vector.hnsw.distance', vmath.python_distance):
        python = build()
    assert native == python
    for left, right in zip(vectors, reversed(vectors), strict=True):
        assert abs(vmath.distance(left, right) - vmath.python_distance(left, right)) <= 1e-12
