"""Prove that an anchored memory survives closing and reopening its store."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from smriti.memory import Anchor, MemoryStore
from smriti.server.service import SmritiService


def run() -> dict[str, object]:
    started = perf_counter()
    with TemporaryDirectory(prefix='smriti-session-demo-') as directory:
        root = Path(directory)
        (root / 'billing.py').write_text(
            'def total(items):\n    return sum(items)\n', encoding='utf-8'
        )
        service = SmritiService(root)
        service.index()
        symbol = next(item for item in service.snapshot().symbols if item.name == 'total')
        database = service.config.data_dir / 'memory.sqlite'
        first_session = MemoryStore(database)
        try:
            fact = first_session.remember(
                'Invoice total sums all item prices.',
                anchors=(Anchor(symbol.id, symbol.content_hash),),
                session='session-one',
                source='demo-code-review',
            )
        finally:
            first_session.close()
        second_session = MemoryStore(database)
        try:
            recalled = second_session.recall('Invoice total')
            assert len(recalled) == 1 and recalled[0].id == fact.id
            assert recalled[0].session == 'session-one'
            report = recalled[0].to_dict()
        finally:
            second_session.close()
        return {
            'scenario': 'session-one closes SQLite; session-two opens it and recalls',
            'seconds': perf_counter() - started,
            'remembered_fact': report,
        }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
