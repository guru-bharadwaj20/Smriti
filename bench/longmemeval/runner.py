"""Run real memory ingestion and retrieval without exposing answer labels."""

import argparse
import hashlib
import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from smriti.memory import MemoryStore


def timestamp(value: str) -> str:
    normalized = value.replace(' (', '(').split('(')[0].strip()
    date = datetime.fromisoformat(normalized.replace('Z', '+00:00'))
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    return date.isoformat()


def ingest(store: MemoryStore, row: dict[str, Any]) -> None:
    """Only unlabelled historical content and dates enter the memory engine."""
    ids, dates, sessions = (
        row[key] for key in ('haystack_session_ids', 'haystack_dates', 'haystack_sessions')
    )
    if not (len(ids) == len(dates) == len(sessions)):
        raise ValueError('Session IDs, dates and histories must align')
    for identity, date, turns in zip(ids, dates, sessions, strict=True):
        text = '\n'.join(f'{turn["role"]}: {turn["content"]}' for turn in turns)
        store.remember(
            text,
            fact_id=str(identity),
            session=str(identity),
            source='LongMemEval-S cleaned session',
            valid_from=timestamp(date),
        )


def evaluate(store: MemoryStore, row: dict[str, Any], k: int = 5) -> dict[str, Any]:
    started = time.perf_counter()
    retrieved = store.recall(str(row['question']), valid_at=timestamp(row['question_date']))[:k]
    identities = [fact.session for fact in retrieved]
    gold = set(row['answer_session_ids'])
    abstention = str(row['question_id']).endswith('_abs')
    return {
        'question_id': row['question_id'],
        'question_type': row['question_type'],
        'abstention': abstention,
        'retrieved_session_ids': identities,
        'gold_session_ids': sorted(gold),
        'session_recall_at_5': len(gold.intersection(identities)) / len(gold) if gold else None,
        'abstained': not identities,
        'query_seconds': time.perf_counter() - started,
    }


def run(dataset: Path, state: Path, output: Path) -> None:
    manifest = json.loads(Path(__file__).with_name('manifest.json').read_text())
    with dataset.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != manifest['sha256'] or dataset.stat().st_size != manifest['size']:
        raise ValueError('Dataset differs from publisher-pinned artifact')
    rows = json.loads(dataset.read_text(encoding='utf-8'))
    if len(rows) != 500 or len({row['question_id'] for row in rows}) != 500:
        raise ValueError('Expected all 500 unique official questions')
    state.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    completed: dict[str, dict[str, Any]] = {}
    if output.exists():
        for line in output.read_text().splitlines():
            record = json.loads(line)
            completed[record['question_id']] = record
    with output.open('a', encoding='utf-8') as stream:
        for number, row in enumerate(rows):
            if row['question_id'] in completed:
                continue
            key = hashlib.sha256(str(row['question_id']).encode()).hexdigest()
            store = MemoryStore(state / f'{key}.sqlite')
            try:
                # Resume may find a partially ingested question. Stable IDs make
                # ingestion idempotent; completed questions are skipped above.
                ingest(store, row)
                record = evaluate(store, row)
            finally:
                store.close()
            record['dataset_sha256'] = digest
            completed[record['question_id']] = record
            stream.write(json.dumps(record) + '\n')
            stream.flush()
            print(f'LongMemEval {number + 1}/500', flush=True)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in completed.values():
        groups['all'].append(record)
        groups[str(record['question_type'])].append(record)
        if record['abstention']:
            groups['abstention'].append(record)
    report = {}
    for category, records in groups.items():
        scored = [r['session_recall_at_5'] for r in records if r['session_recall_at_5'] is not None]
        abstention = [r for r in records if r['abstention']]
        report[category] = {
            'questions': len(records),
            'scored_questions': len(scored),
            'session_recall_at_5': sum(scored) / len(scored) if scored else None,
            'abstention_retrieval_rate': sum(r['abstained'] for r in abstention) / len(abstention)
            if abstention
            else None,
        }
    output.with_suffix('.summary.json').write_text(
        json.dumps(
            {
                'manifest': manifest,
                'metrics': report,
                'answer_accuracy': None,
                'limitations': [
                    'Lexical memory retrieval; no semantic fact extraction.',
                    'Abstention is empty retrieval, not an LLM judgement.',
                    'Concurrent CPU workloads affect timings.',
                ],
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--state', type=Path, default=Path('.smriti/longmemeval/state'))
    parser.add_argument('--output', type=Path, default=Path('bench/results/longmemeval.jsonl'))
    args = parser.parse_args()
    run(args.dataset, args.state, args.output)
