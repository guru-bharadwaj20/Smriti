from concurrent.futures import ThreadPoolExecutor

from smriti.vector.embedding import EmbeddingCache


class FakeEncoder:
    version = 'fixture-model-v1'

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [(float(len(text)), 1.0) for text in texts]


def test_cache_batches_unique_misses_and_preserves_order():
    encoder = FakeEncoder()
    cache = EmbeddingCache(':memory:', encoder)
    assert cache.embed(['a', 'bb', 'a']) == [(1.0, 1.0), (2.0, 1.0), (1.0, 1.0)]
    assert encoder.calls == [['a', 'bb']]
    cache.embed(['bb', 'ccc'])
    assert encoder.calls == [['a', 'bb'], ['ccc']]
    encoder.version = 'fixture-model-v2'
    cache.embed(['a'])
    assert len(encoder.calls) == 3
    cache.close()


def test_cache_cross_thread_reads_and_writes():
    encoder = FakeEncoder()
    cache = EmbeddingCache(':memory:', encoder)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: cache.embed(['same', 'same']), range(8)))
    assert all(result == [(4.0, 1.0), (4.0, 1.0)] for result in results)
    assert encoder.calls == [['same']]
    cache.close()
