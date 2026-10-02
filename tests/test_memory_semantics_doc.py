"""Executable versions of the examples in docs/memory-semantics.md."""

from pathlib import Path

import pytest

from smriti.memory import Anchor, MemoryStore


def texts(facts):
    return sorted(fact.text for fact in facts)


def test_valid_time_and_transaction_time_are_independent(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / 'm.sqlite')
    store.remember('timeout is 30s', fact_id='timeout', valid_from='2026-01-01T00:00:00+00:00')
    believed_before = store.recall()[0].recorded_at
    store.update('timeout', 'timeout is 60s', valid_from='2026-03-01T00:00:00+00:00')
    assert texts(store.recall()) == ['timeout is 60s']
    assert texts(store.recall(valid_at='2026-02-01T00:00:00+00:00')) == ['timeout is 30s']
    assert texts(store.recall(valid_at='2026-04-01T00:00:00+00:00')) == ['timeout is 60s']
    assert texts(store.recall(as_of=believed_before)) == ['timeout is 30s']
    assert store.recall(valid_at='2025-12-31T00:00:00+00:00') == []
    with pytest.raises(ValueError):
        store.recall(valid_at='2026-02-01T00:00:00')
    store.close()


def test_invalidate_and_revert_are_additive(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / 'm.sqlite')
    store.remember('uses sqlite', fact_id='db')
    operation = store.log()[0]['id']
    store.invalidate('db')
    assert store.recall() == []
    invalidation = store.log()[0]['id']
    store.revert(invalidation)
    assert texts(store.recall()) == ['uses sqlite']
    assert len(store.log()) == 3 and operation in {e['id'] for e in store.log()}
    with pytest.raises(ValueError, match='already reverted'):
        store.revert(invalidation)
    store.close()


def test_forget_cascades_and_cannot_be_undone(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / 'm.sqlite')
    store.remember('raw note', fact_id='src', session='s1')
    store.remember('summary of note', fact_id='derived', derived_from=['src'])
    store.remember('unrelated', fact_id='other')
    added = [e['id'] for e in store.log() if e.get('fact_id') == 'src']
    assert sorted(store.forget('src')) == ['derived', 'src']
    assert texts(store.recall()) == ['unrelated']
    store.branch('old')
    store.switch('old')
    assert texts(store.recall()) == ['unrelated']
    with pytest.raises(ValueError, match='Forgotten'):
        store.revert(added[0])
    store.remember('raw note again', fact_id='src2')
    assert store.forget('src') == []
    assert store.verify()
    store.close()


def test_anchor_freshness_states(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / 'm.sqlite')
    store.remember('a', fact_id='a', anchors=[Anchor('sym-a', 'h1')])
    store.remember('b', fact_id='b', anchors=[Anchor('sym-b', 'h2')])
    store.remember('c', fact_id='c', anchors=[Anchor('sym-c', 'h3')])
    store.refresh(
        {'sym-a': 'h1', 'sym-b': 'changed', 'sym-moved': 'h3'}, renames={'sym-c': 'sym-moved'}
    )
    state = {f.id: f.freshness for f in store.recall()}
    assert state == {'a': 'fresh', 'b': 'stale', 'c': 'fresh'}
    store.refresh({'sym-a': 'h1', 'sym-b': 'changed'})
    assert {f.id: f.freshness for f in store.recall()}['c'] == 'orphaned'
    assert [f.id for f in store.recall(include_stale=False)] == ['a']
    store.close()
