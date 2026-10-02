from pathlib import Path

from bench.longmemeval.runner import evaluate, ingest
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
