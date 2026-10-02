import pytest

from smriti.rank.pagerank import personalized_pagerank
from smriti.rank.push import push_pagerank


def test_push_residual_bounds_exact_error_with_dangling_nodes():
    graph = {'a': {'b': 1.0}, 'b': {'c': 0.5, 'a': 0.5}, 'c': {}}
    exact = personalized_pagerank(graph, {'a': 1}, tolerance=1e-12)
    result = push_pagerank(graph, {'a': 1}, tolerance=1e-7)
    assert result.converged
    assert (
        sum(abs(exact[node] - result.scores.get(node, 0)) for node in graph)
        <= result.residual_l1 + 1e-10
    )
    assert sum(result.scores.values()) + result.residual_l1 == pytest.approx(1)
    truncated = push_pagerank(graph, {'a': 1}, max_pushes=1)
    assert not truncated.converged
    assert truncated.pushes == 1


def test_push_rejects_missing_nodes_and_nan():
    with pytest.raises(ValueError):
        push_pagerank({'a': {'missing': 1}}, {'a': 1})
    with pytest.raises(ValueError):
        push_pagerank({'a': {}}, {'a': float('nan')})
