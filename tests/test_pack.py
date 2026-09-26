from smriti.pack.packer import Representation, knapsack


def test_bucket_budget():
    groups = [
        [Representation(str(i), 'omit', '', 0, 0), Representation(str(i), 'body', 'x', 3, 5)]
        for i in range(3)
    ]
    chosen = knapsack(groups, 7, bucket=2)
    assert sum(x.cost for x in chosen) <= 7


def test_oversized_degrades():
    options = [
        Representation('a', 'omit', '', 0, 0),
        Representation('a', 'name', 'f', 1, 1),
        Representation('a', 'body', 'long', 100, 5),
    ]
    assert knapsack([options], 2)[0].level == 'name'


def test_exhaustive_oracle():
    import itertools
    import random

    r = random.Random(55)
    for _ in range(50):
        groups = [
            [Representation(str(i), 'omit', '', 0, 0)]
            + [
                Representation(str(i), str(j), '', r.randrange(1, 10), r.random() * 10)
                for j in range(3)
            ]
            for i in range(4)
        ]
        budget = r.randrange(5, 25)
        gold = max(
            sum(o.value for o in choice)
            for choice in itertools.product(*groups)
            if sum(o.cost for o in choice) <= budget
        )
        assert abs(sum(o.value for o in knapsack(groups, budget)) - gold) < 1e-9


def test_final_recount_enforces_budget():
    from types import SimpleNamespace as S

    from smriti.pack.packer import ContextPacker

    class Counter:
        encoding_name = 'adversarial-test'

        def count(self, text):
            return len(text) + (10000 if 'first' in text and 'second' in text else 0)

    symbols = [
        S(
            id=id,
            path='a.py',
            start_line=i,
            end_line=i + 1,
            qualname=id,
            signature=f'def {id}():',
            docstring='',
            body=f'def {id}(): pass',
            parent_id=None,
            kind='function',
        )
        for i, id in enumerate(['first', 'second'], 1)
    ]
    result = ContextPacker(Counter()).pack(symbols, {'first': 1, 'second': 1}, 500)
    assert result.token_count <= 500
    assert len(result.items) == 1


def test_orphan_methods_are_omitted():
    from smriti.models import Symbol
    from smriti.pack.packer import ContextPacker
    from smriti.pack.tokens import ByteCounter

    method = Symbol(
        'm',
        'a.py',
        'f',
        'C.f',
        'method',
        signature='def f():',
        body='def f(): pass',
        parent_id='missing',
    )
    result = ContextPacker(ByteCounter()).pack([method], {'m': 1.0}, 1000)
    assert result.text == ''
    assert result.omitted_ids == ['m']


def test_full_class_covers_descendant_without_duplicate_body():
    from smriti.models import Symbol
    from smriti.pack.packer import ContextPacker
    from smriti.pack.tokens import ByteCounter

    cls = Symbol(
        'c', 'a.py', 'C', 'C', 'class', signature='class C:', body='class C:\n    def f(self): pass'
    )
    method = Symbol(
        'm',
        'a.py',
        'f',
        'C.f',
        'method',
        start_line=2,
        end_line=2,
        signature='def f(self):',
        body='def f(self): pass',
        parent_id='c',
    )
    result = ContextPacker(ByteCounter()).pack([cls, method], {'c': 2.0, 'm': 1.0}, 1000)
    assert result.text.count('def f(self): pass') == 1
    assert result.covered_ids == ['c', 'm']
    assert not result.omitted_ids


def test_nonfinite_and_negative_pack_values_rejected():
    import pytest

    for value in [-1.0, float('nan'), float('inf')]:
        with pytest.raises(ValueError):
            knapsack([[Representation('a', 'body', '', 1, value)]], 10)
    with pytest.raises(ValueError):
        knapsack([[Representation('a', 'body', '', -1, 1.0)]], 10)
