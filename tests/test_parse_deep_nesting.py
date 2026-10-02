import sys

from smriti.parse import SourceParser


def test_deeply_nested_python_does_not_hit_recursion_limit() -> None:
    depth = sys.getrecursionlimit() * 3
    source = (
        'def table():\n    return '
        + '[' * depth
        + ']' * depth
        + '\n\n\ndef after():\n    return table()\n'
    )
    result = SourceParser().parse('deep.py', source)
    assert [s.qualname for s in result.symbols] == ['deep', 'deep.table', 'deep.after']
    assert any(call['name'] == 'table' for call in result.calls)


def test_deeply_nested_c_does_not_hit_recursion_limit() -> None:
    depth = sys.getrecursionlimit() * 3
    source = (
        'int f(void) { return '
        + '(' * depth
        + '1'
        + ')' * depth
        + '; }\nint g(void) { return f(); }\n'
    )
    result = SourceParser().parse('deep.c', source, 'c')
    assert {s.name for s in result.symbols} >= {'f', 'g'}
