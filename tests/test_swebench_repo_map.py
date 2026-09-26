from bench.swebench.repo_map_baseline import repo_map_baseline
from smriti.models import Edge, Symbol


def test_repo_map_filters_external_nodes_and_orders_scores():
    def symbol(identity, name):
        return Symbol(
            identity,
            'a.py',
            name,
            name,
            'function',
            1,
            2,
            0,
            20,
            'def ' + name + '():',
            '',
            'return 1',
            'hash',
            None,
        )

    symbols = [symbol('a', 'unrelated'), symbol('z', 'wanted')]
    edges = [Edge('z', 'outside', 'calls', 1.0)]
    hits = repo_map_baseline(symbols, edges, 'wanted')
    assert hits[0].id == 'z'
    assert all(hit.id in {'a', 'z'} for hit in hits)
    assert [hit.score for hit in hits] == sorted((hit.score for hit in hits), reverse=True)
