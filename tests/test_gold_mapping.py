from bench.swebench.ground_truth import ChangedFile
from bench.swebench.mapping import gold_base_functions
from smriti.models import Symbol


def test_context_neighbors_and_new_functions_do_not_inflate_base_gold() -> None:
    symbols = [Symbol('first', 'a.py', 'first', 'first', 'function', 1, 2),
               Symbol('second', 'a.py', 'second', 'second', 'function', 3, 5)]
    assert gold_base_functions([ChangedFile('a.py', 'a.py', (4,), ())], symbols) == {'second'}
    assert gold_base_functions([ChangedFile(None, 'new.py', (), (0,))], symbols) == set()


def test_nested_function_uses_specific_inner_symbol() -> None:
    symbols = [Symbol('outer', 'a.py', 'outer', 'outer', 'function', 1, 10),
               Symbol('inner', 'a.py', 'inner', 'outer.inner', 'function', 4, 6)]
    assert gold_base_functions([ChangedFile('a.py', 'a.py', (5,), ())], symbols) == {'inner'}
