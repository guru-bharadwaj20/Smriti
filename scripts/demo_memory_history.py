"""Exercise rename identity, stale anchors, branch conflict, merge and revert."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from smriti.memory import Anchor, MemoryStore, MergeConflict
from smriti.parse import SourceParser
from smriti.watch import preserve_symbol_ids


def run() -> dict[str, object]:
    started = perf_counter()
    with TemporaryDirectory(prefix='smriti-history-demo-') as directory:
        root = Path(directory)
        parser = SourceParser()
        original = parser.parse('worker.py', 'def work():\n    return 1\n').symbols
        before = next(symbol for symbol in original if symbol.kind == 'function')
        renamed, mapping = preserve_symbol_ids(
            original, parser.parse('renamed.py', 'def work():\n    return 1\n').symbols
        )
        after = next(symbol for symbol in renamed if symbol.kind == 'function')
        assert after.id == before.id and after.path == 'renamed.py' and mapping
        store = MemoryStore(root / 'memory.sqlite')
        try:
            fact = store.remember(
                'Work returns one.', anchors=(Anchor(before.id, before.content_hash),)
            )
            store.refresh({symbol.id: symbol.content_hash for symbol in renamed})
            assert store.recall()[0].freshness == 'fresh'
            edited, _ = preserve_symbol_ids(
                renamed, parser.parse('renamed.py', 'def work():\n    return 2\n').symbols
            )
            store.refresh({symbol.id: symbol.content_hash for symbol in edited}, commit='demo-edit')
            stale = store.recall()[0]
            assert stale.freshness == 'stale' and stale.triggering_commit == 'demo-edit'
            store.branch('feature')
            store.switch('feature')
            store.update(fact.id, 'Feature review: work returns two.')
            store.switch('main')
            store.update(fact.id, 'Main review: check work before use.')
            preview = store.merge_preview('feature')
            assert fact.id in preview['conflicts']
            try:
                store.merge('feature')
            except MergeConflict:
                conflict_blocked = True
            else:
                raise AssertionError('Conflict must require explicit resolution')
            merge = store.merge('feature', resolutions={fact.id: 'theirs'})
            merged_text = store.recall()[0].text
            assert merged_text == 'Feature review: work returns two.'
            reverted = store.revert(merge)
            restored_text = store.recall()[0].text
            assert restored_text == 'Main review: check work before use.'
            assert store.verify()
            return {
                'scenario': 'Parser identity preservation plus real memory operation history',
                'seconds': perf_counter() - started,
                'rename_preserved_id': after.id == before.id,
                'stale_fact': stale.to_dict(),
                'branches': store.branches(),
                'conflict_blocked': conflict_blocked,
                'merge_operation': merge,
                'merged_text': merged_text,
                'revert_operation': reverted,
                'restored_text': restored_text,
                'scope': 'Memory branches exercised directly; Git ref synchronization is separate.',
            }
        finally:
            store.close()


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
