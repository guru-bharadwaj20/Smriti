from smriti.rank.hybrid import reciprocal_rank_fusion
from smriti.rank.pagerank import personalized_pagerank


def test_analytic_stationary_distribution():
    scores = personalized_pagerank({'a': {'b': 1}, 'b': {}}, {'a': 1}, damping=0.5)
    assert abs(scores['a'] - 2 / 3) < 1e-9
    assert abs(scores['b'] - 1 / 3) < 1e-9


def test_fusion():
    assert list(reciprocal_rank_fusion([['a', 'b'], ['b', 'c']], constant=1))[0] == 'b'


def test_numeric_inputs_and_missing_nodes():
    import pytest

    from smriti.rank.pagerank import adjacency

    assert adjacency(['a'], [('a', 'missing', 'calls')]) == {'a': {}}
    for value in [float('nan'), float('inf'), -1]:
        with pytest.raises(ValueError):
            reciprocal_rank_fusion([['a']], weights=[value])
        with pytest.raises(ValueError):
            personalized_pagerank({'a': {}}, {'a': value})
        with pytest.raises(ValueError):
            personalized_pagerank({'a': {'a': value}}, {'a': 1})
    with pytest.raises(ValueError):
        personalized_pagerank({'a': {'missing': 1}}, {'a': 1})


def test_cache_results_do_not_alias_storage():
    from smriti.rank.hybrid import RankingCache

    cache = RankingCache()
    cache.put('1', 'Hello', {'a': 1.0})
    retrieved = cache.get('1', 'hello')
    retrieved['a'] = 99
    assert cache.get('1', 'HELLO') == {'a': 1.0}
    cache.invalidate('2')
    assert cache.get('1', 'hello') is None
