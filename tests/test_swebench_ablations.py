from bench.swebench.ablations import context, variant
from smriti.models import Edge, Symbol
from smriti.server.retrieval import Retriever
from smriti.server.snapshots import IndexSnapshot


def test_variants_preserve_production_state_and_budget():
    symbol = Symbol(
        's',
        'a.py',
        'work',
        'work',
        'function',
        1,
        2,
        0,
        30,
        'def work():',
        '',
        'def work():\n    return 1',
        'hash',
        None,
    )
    engine = Retriever(IndexSnapshot(1, (symbol,), (), {'a.py': 'hash'}))
    assert variant(engine, 'full').rank('work') == engine.rank('work')
    assert variant(engine, 'no_vector').vector is None
    assert variant(engine, 'no_graph').snapshot.edges == ()
    for name in ('full', 'no_vector', 'no_graph', 'greedy'):
        for budget in (0, 20, 100):
            result = context(engine, name, 'work', budget)
            assert result.token_count <= budget
    assert engine.snapshot.symbols == (symbol,)


def test_memoized_components_are_never_shared_across_ablations():
    def symbol(id, name, body):
        return Symbol(
            id, 'a.py', name, name, 'function', 1, 2, 0, 30, f'def {name}():', '', body, id, None
        )

    caller = symbol('a', 'caller', 'def caller():\n    return helper()')
    helper = symbol('b', 'helper', 'def helper():\n    return 1')
    edge = Edge('a', 'b', 'calls', 1.0)
    engine = Retriever(IndexSnapshot(1, (caller, helper), (edge,), {'a.py': 'hash'}))
    graph_free = Retriever(IndexSnapshot(1, (caller, helper), (), {'a.py': 'hash'}))
    full = engine.components('caller')
    assert engine.components('caller') is full
    ablated = variant(engine, 'no_graph').components('caller')
    assert ablated == graph_free.components('caller')
    assert ablated != full
