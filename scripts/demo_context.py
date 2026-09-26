"""Retrieve real indexed code for an issue inside an 8,000-token budget."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from smriti.server.service import SmritiService


def run() -> dict[str, object]:
    with TemporaryDirectory(prefix='smriti-context-demo-') as directory:
        root = Path(directory)
        (root / 'billing.py').write_text(
            'def total(items, discount=0):\n'
            '    "Calculate invoice total after discount."\n'
            '    return sum(items) - discount\n\n'
            'def invoice(items):\n    return total(items)\n',
            encoding='utf-8',
        )
        (root / 'test_billing.py').write_text(
            'from billing import total\n\n'
            'def test_discount():\n    assert total([10, 20], 5) == 25\n',
            encoding='utf-8',
        )
        service = SmritiService(root)
        service.index()
        task = 'Fix invoice total discount calculation and check its callers and tests.'
        started = perf_counter()
        context = service.context(task, budget=8000)
        elapsed = perf_counter() - started
        assert 0 < context.token_count <= context.budget == 8000
        assert 'total' in context.text and context.items
        return {
            'scenario': 'issue retrieval from a small synthetic billing repository',
            'task': task,
            'seconds': elapsed,
            'tokens': context.token_count,
            'budget': context.budget,
            'tokenizer': context.tokenizer,
            'selected_symbols': len(context.items),
            'text': context.text,
            'scope': 'Functional demo, not SWE-bench retrieval performance.',
        }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
