"""End-to-end demo: index, retrieve, remember anchored facts, detect staleness, forget."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from smriti.server.service import MemoryService, SmritiService


def run() -> dict[str, object]:
    started = perf_counter()
    with TemporaryDirectory(prefix='smriti-integration-demo-') as directory:
        root = Path(directory)
        source = root / 'billing.py'
        source.write_text(
            'def total(items, discount=0):\n    return sum(items) - discount\n\n\n'
            'def invoice(items):\n    return total(items)\n',
            encoding='utf-8',
        )
        code = SmritiService(root)
        first = code.index()
        context = code.context('fix invoice total discount', 2000)
        assert 'total' in context.text and context.token_count <= 2000
        symbol = next(s for s in code.find_symbol('total') if s.kind == 'function')
        callers = code.calls('total', incoming=True)
        invoice = next(s for s in code.find_symbol('invoice') if s.kind == 'function')
        assert [edge.source for edge in callers] == [invoice.id]
        memory = MemoryService(root)
        try:
            fact = memory.remember(
                'total() subtracts the discount once per invoice.',
                anchors=[{'symbol_id': symbol.id, 'content_hash': symbol.content_hash}],
                source='review',
            )
            source.write_text(
                source.read_text(encoding='utf-8').replace('- discount', '- discount * len(items)'),
                encoding='utf-8',
            )
            second = code.index()
            hashes = {s.id: s.content_hash for s in code.snapshot().symbols}
            memory.store.refresh(hashes, commit='demo-edit')
            recalled = memory.recall('discount')
            assert recalled[0]['id'] == fact['id'] and recalled[0]['freshness'] == 'stale'
            forgotten = memory.forget(source='review')
            assert forgotten == [fact['id']] and memory.recall() == []
            operations = len(memory.log())
        finally:
            memory.close()
        return {
            'scenario': 'code retrieval plus anchored memory lifecycle on a synthetic repository',
            'seconds': perf_counter() - started,
            'index_versions': [first.version, second.version],
            'context_tokens': context.token_count,
            'callers_of_total': len(callers),
            'stale_after_edit': True,
            'forgotten': len(forgotten),
            'memory_operations': operations,
        }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
