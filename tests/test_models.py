import pytest

from smriti.models import Edge, Symbol


def test_source_range_and_confidence_validation() -> None:
    with pytest.raises(ValueError):
        Symbol('s', 'a.py', 'f', 'f', 'function', end_line=0)
    with pytest.raises(ValueError):
        Edge('a', 'b', 'calls', confidence=1.1)
    assert Symbol('s', 'a.py', 'f', 'f', 'function').start_line == 1
