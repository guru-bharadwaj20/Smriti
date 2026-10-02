"""Profile actual custom HNSW, then compare optional native distance identically."""

import cProfile
import importlib.util
import io
import json
import pstats
import random
import shutil
import time
from pathlib import Path
from unittest.mock import patch

from bench.swebench.hardware import hardware_metadata
from smriti.vector.hnsw import HNSWIndex
from smriti.vector.math import distance, normalize


def run(count=120, dimensions=384, seed=17):
    randomizer = random.Random(seed)
    vectors = [normalize([randomizer.gauss(0, 1) for _ in range(dimensions)]) for _ in range(count)]
    queries = vectors[:20]
    profiler = cProfile.Profile()
    started = time.perf_counter()
    with profiler:
        index = HNSWIndex(seed=seed)
        for number, vector in enumerate(vectors):
            index.add(str(number), vector)
        expected = [index.search(query, 10) for query in queries]
    elapsed = time.perf_counter() - started
    report = io.StringIO()
    pstats.Stats(profiler, stream=report).sort_stats('cumulative').print_stats(20)
    result = {
        'hardware': hardware_metadata(),
        'seed': seed,
        'vectors': count,
        'dimensions': dimensions,
        'queries': len(queries),
        'python_profiled_seconds': elapsed,
        'cumulative_profile': report.getvalue(),
        'cargo': shutil.which('cargo'),
        'rustc': shutil.which('rustc'),
        'native_available': importlib.util.find_spec('smriti_native') is not None,
    }
    if not result['native_available']:
        result['native_status'] = 'Not built; no speedup or correctness comparison claimed.'
        return result
    import smriti_native

    for left, right in zip(vectors, reversed(vectors), strict=True):
        if abs(smriti_native.distance(left, right) - distance(left, right)) > 1e-12:
            raise AssertionError('Native distance parity failed')
    started = time.perf_counter()
    with patch('smriti.vector.hnsw.distance', smriti_native.distance):
        native = HNSWIndex(seed=seed)
        for number, vector in enumerate(vectors):
            native.add(str(number), vector)
        actual = [native.search(query, 10) for query in queries]
    native_seconds = time.perf_counter() - started
    assert native.graph == index.graph, 'Seeded graph differs with native distance'
    assert [[h.id for h in hits] for hits in actual] == [[h.id for h in hits] for hits in expected]
    # Profile overhead is excluded from the speed comparison.
    started = time.perf_counter()
    plain = HNSWIndex(seed=seed)
    for number, vector in enumerate(vectors):
        plain.add(str(number), vector)
    for query in queries:
        plain.search(query, 10)
    plain_seconds = time.perf_counter() - started
    result.update(
        {
            'python_unprofiled_seconds': plain_seconds,
            'native_seconds': native_seconds,
            'speedup': plain_seconds / native_seconds,
            'graph_and_query_ids_identical': True,
        }
    )
    return result


if __name__ == '__main__':
    result = run()
    Path('bench/vector/native_profile.json').write_text(json.dumps(result, indent=2) + '\n')
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != 'cumulative_profile'}, indent=2
        )
    )
