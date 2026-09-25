import pytest

from bench.swebench.function_metrics import function_recall_at_k


def test_recall_uses_unique_base_symbols_not_duplicate_hits() -> None:
    assert function_recall_at_k(['f', 'f', 'g'], {'f', 'g'}, 2) == 1
    assert function_recall_at_k(['f', 'wrong'], {'f', 'g'}, 2) == 0.5
    assert function_recall_at_k(['f'], {'f'}, 0) == 0
    assert function_recall_at_k([], set(), 10) is None
    with pytest.raises(ValueError):
        function_recall_at_k([], {'f'}, -1)
