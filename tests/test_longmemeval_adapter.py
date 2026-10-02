from pathlib import Path

import pytest

from bench.longmemeval.runner import evaluate, ingest, timestamp
from smriti.memory import MemoryStore


def test_session_ingestion_excludes_labels_and_future_sessions(tmp_path: Path) -> None:
    row = {
        'question_id': 'temporal',
        'question_type': 'temporal-reasoning',
        'question': 'favorite sport',
        'question_date': '2025-01-02',
        'haystack_session_ids': ['past', 'future'],
        'haystack_dates': ['2025-01-01', '2025-02-01'],
        'haystack_sessions': [
            [{'role': 'user', 'content': 'favorite sport tennis', 'has_answer': True}],
            [{'role': 'user', 'content': 'favorite sport soccer'}],
        ],
        'answer': 'SECRET GOLD ANSWER',
        'answer_session_ids': ['past'],
    }
    store = MemoryStore(tmp_path / 'memory.sqlite')
    ingest(store, row)
    assert all(
        'SECRET GOLD' not in fact.text and 'has_answer' not in fact.text for fact in store.recall()
    )
    result = evaluate(store, row)
    assert result['retrieved_session_ids'] == ['past']
    assert result['session_recall_at_5'] == 1.0
    store.close()


def test_published_date_format_keeps_time_of_day():
    assert timestamp('2023/05/20 (Sat) 02:21') == '2023-05-20T02:21:00+00:00'
    assert timestamp('2025-01-02') == '2025-01-02T00:00:00+00:00'


def test_identical_repeated_session_is_ingested_once(tmp_path: Path) -> None:
    turns = [{'role': 'user', 'content': 'same history'}]
    row = {
        'haystack_session_ids': ['s', 's'],
        'haystack_dates': ['2023/05/23 (Tue) 23:54', '2023/05/29 (Mon) 13:56'],
        'haystack_sessions': [turns, turns],
    }
    store = MemoryStore(tmp_path / 'memory.sqlite')
    ingest(store, row)
    assert [fact.id for fact in store.recall()] == ['s']
    changed = MemoryStore(tmp_path / 'changed.sqlite')
    row['haystack_sessions'] = [turns, [{'role': 'user', 'content': 'different'}]]
    with pytest.raises(ValueError, match='different content'):
        ingest(changed, row)
    store.close()
    changed.close()
