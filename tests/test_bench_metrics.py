from bench.swebench.metrics import file_recall_at_k


def test_file_recall_deduplicates_and_does_not_reward_empty_gold() -> None:
    assert file_recall_at_k(['a.py', 'a.py', 'b.py'], {'a.py', 'b.py'}, 2) == 1
    assert file_recall_at_k(['a.py'], {'a.py', 'b.py'}, 1) == 0.5
    assert file_recall_at_k([], set(), 10) is None
