from bench.swebench.budget_metrics import recall_at_budget
from smriti.models import Symbol


def test_eight_thousand_token_recall():
    symbols = [
        Symbol('a', 'a.py', 'f', 'f', 'function', signature='def f():', body='def f(): pass')
    ]
    result = recall_at_budget(symbols, {'a': 1.0}, {'a'}, 8192)
    assert result['function_recall'] == 1.0
    assert result['tokens'] <= 8192
