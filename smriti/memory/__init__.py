"""Durable, repository-local facts for coding agents."""

from __future__ import annotations

import datetime as _dt
import json
import math
import sqlite3
import uuid
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..models import Symbol
from .operations import Operation, OperationLog, canonical
from .temporal import TemporalVersion, Timeline, TransactionInterval, ValidInterval, timestamp


@dataclass(frozen=True)
class Anchor:
    symbol_id: str
    content_hash: str = ''


@dataclass(frozen=True)
class Fact:
    id: str
    text: str
    user: str | None = None
    session: str | None = None
    tool: str | None = None
    source: str | None = None
    confidence: float = 1.0
    anchors: tuple[Anchor, ...] = ()
    freshness: str = 'fresh'
    freshness_reason: str | None = None
    triggering_commit: str | None = None
    subject: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    recorded_at: str | None = None
    derived_from: tuple[str, ...] = ()
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            'scope': self.scope,
            'requires_revalidation': self.freshness != 'fresh',
        }

    @property
    def scope(self) -> str:
        return 'symbol' if self.anchors else 'project'


class MergeConflict(ValueError):
    def __init__(self, conflicts: dict[str, dict[str, Any]]) -> None:
        self.conflicts = conflicts
        super().__init__('Unresolved memory merge conflicts: ' + ', '.join(sorted(conflicts)))


class MemoryStore:
    """SQLite-backed fact store. Each write is atomic and survives restart."""

    def __init__(self, db_path: str | Path, *, clock: Callable[[], datetime] | None = None) -> None:
        self.db = sqlite3.connect(str(db_path))
        self.db.execute('PRAGMA secure_delete=ON')
        self._clock = clock or (lambda: datetime.now(_dt.UTC))
        schemas = [
            'CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS fact_anchors (fact_id TEXT, symbol_id TEXT, content_hash TEXT, PRIMARY KEY (fact_id, symbol_id))',
            'CREATE TABLE IF NOT EXISTS fact_audit (seq INTEGER PRIMARY KEY, fact_id TEXT, before_payload TEXT, after_payload TEXT)',
            'CREATE TABLE IF NOT EXISTS conflict_audit (seq INTEGER PRIMARY KEY, fact_id TEXT, candidate_ids TEXT, winner_id TEXT)',
            'CREATE TABLE IF NOT EXISTS memory_meta (key TEXT PRIMARY KEY, value TEXT)',
        ]
        for sql in schemas:
            self.db.execute(sql)
        self.db.execute("INSERT OR IGNORE INTO memory_meta VALUES ('head',NULL)")
        self.db.commit()
        self.operations = OperationLog(self.db)
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS memory_derivations (source_id TEXT,derived_id TEXT,PRIMARY KEY(source_id,derived_id))'
        )
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS memory_branches (name TEXT PRIMARY KEY,head TEXT)'
        )
        self.db.execute("INSERT OR IGNORE INTO memory_meta VALUES ('branch','main')")
        self.db.execute("INSERT OR IGNORE INTO memory_branches VALUES ('main',?)", (self.head,))
        self.db.execute('CREATE TABLE IF NOT EXISTS memory_purged (fact_id TEXT PRIMARY KEY)')
        self.db.commit()
        self._savepoint_seq = 0

    def close(self) -> None:
        self.db.close()

    def remember(
        self,
        text: str,
        *,
        fact_id: str | None = None,
        user: str | None = None,
        session: str | None = None,
        tool: str | None = None,
        source: str | None = None,
        confidence: float = 1.0,
        anchors: Iterable[Anchor | dict[str, str]] = (),
        selected_context: Iterable[Symbol | dict[str, str]] = (),
        subject: str | None = None,
        valid_from: datetime | str | None = None,
        valid_to: datetime | str | None = None,
        derived_from: Iterable[str] = (),
    ) -> Fact:
        with self._atomic():
            if not isinstance(text, str) or not text.strip():
                raise ValueError('Fact text must be nonempty')
            if (
                not isinstance(confidence, (int, float))
                or not math.isfinite(confidence)
                or (not 0 <= confidence <= 1)
            ):
                raise ValueError('Confidence must be finite in [0,1]')
            for value in (user, session, tool, source, subject):
                if value is not None and (not isinstance(value, str) or not value.strip()):
                    raise ValueError('Metadata values must be nonempty strings')
            if not anchors:
                anchors = tuple(
                    Anchor(s['symbol_id'], s['content_hash'])
                    if isinstance(s, dict)
                    else Anchor(s.id, s.content_hash)
                    for s in selected_context
                )
            normalized_anchors = tuple(Anchor(**a) if isinstance(a, dict) else a for a in anchors)
            if any(
                not isinstance(a, Anchor) or not a.symbol_id or (not a.content_hash)
                for a in normalized_anchors
            ):
                raise ValueError('Anchors require symbol IDs and hashes')
            if len({a.symbol_id for a in normalized_anchors}) != len(normalized_anchors):
                raise ValueError('Duplicate anchors are not allowed')
            if self.is_purged(fact_id):
                raise ValueError('Forgotten fact IDs cannot be reused')
            recorded_at = self._event_time()
            valid = ValidInterval(valid_from or recorded_at, valid_to)
            fact = Fact(
                fact_id or uuid.uuid4().hex,
                text,
                user,
                session,
                tool,
                source,
                float(confidence),
                normalized_anchors,
            )
            derived_from = tuple(dict.fromkeys(derived_from))
            known = {f.id for f in self.recall()}
            if any(
                source_id not in known or self.is_purged(source_id) for source_id in derived_from
            ):
                raise ValueError('Derivation sources must exist on the active branch')
            self._validate_derivations(fact.id, derived_from)
            fact = replace(
                fact,
                derived_from=derived_from,
                subject=subject,
                created_at=recorded_at,
                valid_from=valid.start.isoformat(),
                valid_to=valid.end.isoformat() if valid.end else None,
                recorded_at=recorded_at,
            )
            with self._atomic():
                self.db.execute(
                    'INSERT INTO facts VALUES (?,?)', (fact.id, canonical(asdict(fact)))
                )
                self.db.executemany(
                    'INSERT INTO fact_anchors VALUES (?,?,?)',
                    [(fact.id, a.symbol_id, a.content_hash) for a in normalized_anchors],
                )
                self.db.executemany(
                    'INSERT OR IGNORE INTO memory_derivations VALUES (?,?)',
                    [(source_id, fact.id) for source_id in derived_from],
                )
                self._record('add', fact.id, asdict(fact), recorded_at=recorded_at)
            return fact

    def recall(
        self,
        query: str = '',
        *,
        valid_at: datetime | str | None = None,
        as_of: datetime | str | None = None,
        include_stale: bool = True,
    ) -> list[Fact]:
        if valid_at is None and as_of is None:
            facts = [
                self._decode(row[0])
                for row in self.db.execute('SELECT payload FROM facts ORDER BY id')
            ]
        else:
            now = timestamp(self._clock())
            facts = [
                self._decode(canonical(v.payload))
                for v in self.timeline().query(valid_at or now, as_of or now)
            ]
        return self._rank_recall(facts, query, include_stale)

    @staticmethod
    def _decode(payload: str) -> Fact:
        data = json.loads(payload)
        data['anchors'] = tuple(Anchor(**a) for a in data.get('anchors', ()))
        data['derived_from'] = tuple(data.get('derived_from', ()))
        return Fact(**data)

    def _save(self, fact: Fact) -> Fact:
        with self._atomic():
            fact = replace(fact, recorded_at=self._event_time())
            previous = self.db.execute(
                'SELECT payload FROM facts WHERE id=?', (fact.id,)
            ).fetchone()
            if previous is None:
                raise KeyError(fact.id)
            self.db.execute(
                'INSERT INTO fact_audit(fact_id,before_payload,after_payload) VALUES (?,?,?)',
                (fact.id, previous[0], canonical(asdict(fact))),
            )
            self.db.execute(
                'UPDATE facts SET payload=? WHERE id=?', (canonical(asdict(fact)), fact.id)
            )
            self.db.execute('DELETE FROM fact_anchors WHERE fact_id=?', (fact.id,))
            self.db.executemany(
                'INSERT INTO fact_anchors VALUES (?,?,?)',
                [(fact.id, a.symbol_id, a.content_hash) for a in fact.anchors],
            )
            self._record('update', fact.id, asdict(fact), recorded_at=fact.recorded_at)
        return fact

    def refresh(
        self,
        symbols: dict[str, str],
        *,
        renames: dict[str, str] | None = None,
        commit: str | None = None,
    ) -> list[Fact]:
        """symbols maps stable symbol IDs to current content hashes."""
        with self._atomic():
            renames = renames or {}
            changes = []
            for fact in self.recall():
                moved = tuple(
                    Anchor(renames[a.symbol_id], a.content_hash)
                    if a.symbol_id in renames
                    and symbols.get(renames[a.symbol_id]) == a.content_hash
                    else a
                    for a in fact.anchors
                )
                if moved != fact.anchors:
                    fact = self._save(replace(fact, anchors=moved))
                    changes.append(fact)
                if any(a.symbol_id not in symbols for a in fact.anchors):
                    changes.append(
                        self._save(
                            replace(
                                fact,
                                freshness='orphaned',
                                freshness_reason='anchor_deleted',
                                triggering_commit=commit,
                            )
                        )
                    )
                elif any(
                    a.symbol_id in symbols and symbols[a.symbol_id] != a.content_hash
                    for a in fact.anchors
                ):
                    changes.append(
                        self._save(
                            replace(
                                fact,
                                freshness='stale',
                                freshness_reason='anchor_changed',
                                triggering_commit=commit,
                            )
                        )
                    )
            return changes

    def anchor_states(self, fact_id: str, symbols: dict[str, str]) -> dict[str, str]:
        fact = next((f for f in self.recall() if f.id == fact_id), None)
        if fact is None:
            raise KeyError(fact_id)
        return {
            a.symbol_id: 'orphaned'
            if a.symbol_id not in symbols
            else 'fresh'
            if symbols[a.symbol_id] == a.content_hash
            else 'stale'
            for a in fact.anchors
        }

    def revalidate(
        self, fact_id: str, symbols: dict[str, str], *, commit: str | None = None
    ) -> Fact:
        with self._atomic():
            fact = next((f for f in self.recall() if f.id == fact_id), None)
            if fact is None:
                raise KeyError(fact_id)
            if any(a.symbol_id not in symbols for a in fact.anchors):
                raise ValueError('Cannot revalidate a deleted anchor')
            anchors = tuple(Anchor(a.symbol_id, symbols[a.symbol_id]) for a in fact.anchors)
            return self._save(
                replace(
                    fact,
                    anchors=anchors,
                    freshness='fresh',
                    freshness_reason='revalidated',
                    triggering_commit=commit,
                )
            )

    def audit(self, fact_id: str) -> list[dict[str, Fact | None]]:
        return [
            {'before': self._decode(before) if before else None, 'after': self._decode(after)}
            for before, after in self.db.execute(
                'SELECT before_payload,after_payload FROM fact_audit WHERE fact_id=? ORDER BY seq',
                (fact_id,),
            )
        ]

    def contradictions(self, fact_id: str) -> list[Fact]:
        fact = next((f for f in self.recall() if f.id == fact_id), None)
        if fact is None:
            raise KeyError(fact_id)
        if not fact.subject:
            return []
        return [
            f
            for f in self.recall()
            if f.id != fact.id and f.subject == fact.subject and (f.text != fact.text)
        ]

    @staticmethod
    def relatedness(
        left: Fact, right: Fact, left_vector: Sequence[float], right_vector: Sequence[float]
    ) -> float:
        if len(left_vector) != len(right_vector) or not left_vector:
            raise ValueError('Embedding dimensions must match and be nonempty')
        if not all(math.isfinite(x) for x in (*left_vector, *right_vector)):
            raise ValueError('Embeddings must be finite')
        norm = math.sqrt(sum(x * x for x in left_vector) * sum(x * x for x in right_vector))
        cosine = (
            sum((x * y for x, y in zip(left_vector, right_vector, strict=True))) / norm
            if norm
            else 0.0
        )
        a, b = ({x.symbol_id for x in left.anchors}, {x.symbol_id for x in right.anchors})
        overlap = len(a & b) / len(a | b) if a | b else 0.0
        return 0.7 * max(0.0, cosine) + 0.3 * overlap

    def preferred(self, fact_id: str, source_priority: dict[str, int] | None = None) -> Fact:
        fact = next((f for f in self.recall() if f.id == fact_id), None)
        if fact is None:
            raise KeyError(fact_id)
        priorities = source_priority or {'code': 3, 'test': 2, 'user': 1}
        candidates = [fact, *self.contradictions(fact_id)]
        winner = max(
            candidates,
            key=lambda f: (
                priorities.get(f.source or '', 0),
                *self._revision_order(f),
                f.confidence,
                f.id,
            ),
        )
        with self._atomic():
            self.db.execute(
                'INSERT INTO conflict_audit(fact_id,candidate_ids,winner_id) VALUES (?,?,?)',
                (fact_id, json.dumps(sorted(f.id for f in candidates)), winner.id),
            )
        return winner

    def conflict_history(self, fact_id: str) -> list[dict[str, Any]]:
        return [
            {'candidates': json.loads(c), 'winner': w}
            for c, w in self.db.execute(
                'SELECT candidate_ids,winner_id FROM conflict_audit WHERE fact_id=? ORDER BY seq',
                (fact_id,),
            )
        ]

    def _rank_recall(self, facts: list[Fact], query: str, include_stale: bool) -> list[Fact]:
        facts = [f for f in facts if include_stale or f.freshness == 'fresh']
        scores: dict[str, float]
        if query.strip():
            from ..lexical.index import BM25Index

            index = BM25Index()
            for fact in facts:
                index.add(
                    fact.id,
                    {
                        'signature': ' '.join(a.symbol_id for a in fact.anchors),
                        'docstring': fact.subject or '',
                        'body': fact.text,
                    },
                )
            scores = {hit.id: hit.score for hit in index.search(query, k=len(facts))}
            facts = [f for f in facts if f.id in scores]
        else:
            scores = {}
        return sorted(
            facts,
            key=lambda f: (
                {'fresh': 0, 'stale': 1, 'orphaned': 2}[f.freshness],
                -scores.get(f.id, 0.0),
                -f.confidence,
                f.id,
            ),
        )

    def _revision_order(self, fact: Fact) -> tuple[str, str, int]:
        row = self.db.execute('SELECT rowid FROM facts WHERE id=?', (fact.id,)).fetchone()
        valid_from = getattr(fact, 'valid_from', None) or fact.created_at or ''
        recorded_at = getattr(fact, 'recorded_at', None) or fact.created_at or ''
        return (str(valid_from), str(recorded_at), int(row[0]) if row else 0)

    @property
    def head(self) -> str | None:
        row = self.db.execute("SELECT value FROM memory_meta WHERE key='head'").fetchone()
        if row is None:
            raise ValueError('Missing active memory head')
        return str(row[0]) if row[0] is not None else None

    def _event_time(self) -> str:
        point = timestamp(self._clock())
        if self.head:
            prior = timestamp(self.operations.get(self.head).recorded_at)
            if point <= prior:
                point = prior + timedelta(microseconds=1)
        return point.isoformat()

    def _record(
        self,
        kind: str,
        fact_id: str | None = None,
        payload: dict[str, Any] | None = None,
        *,
        metadata: dict[str, Any] | None = None,
        recorded_at: str | None = None,
        parents: Iterable[str] | None = None,
    ) -> Operation:
        parents = tuple(parents if parents is not None else (self.head,) if self.head else ())
        point = timestamp(recorded_at or self._event_time())
        for parent in parents:
            prior = timestamp(self.operations.get(parent).recorded_at)
            if point <= prior:
                point = prior + timedelta(microseconds=1)
        op = self.operations.append_uncommitted(
            kind,
            fact_id,
            payload,
            parents=parents,
            recorded_at=point.isoformat(),
            metadata=metadata,
        )
        self.db.execute("UPDATE memory_meta SET value=? WHERE key='head'", (op.id,))
        self.db.execute(
            'UPDATE memory_branches SET head=? WHERE name=?', (op.id, self.current_branch)
        )
        return op

    def replay(self, head: str | None = None) -> dict[str, Fact]:
        state: dict[str, Fact] = {}
        for op in self.operations.ancestry(head if head is not None else self.head):
            if op.kind in ('merge', 'restore'):
                state = {}
                for fid, payload_hash in op.metadata['state'].items():
                    row = self.db.execute(
                        'SELECT payload FROM memory_blobs WHERE digest=?', (payload_hash,)
                    ).fetchone()
                    if row and (not self.is_purged(fid)):
                        state[fid] = self._decode(row[0])
                continue
            if self.is_purged(op.fact_id):
                continue
            if op.fact_id is None:
                raise ValueError('Fact event requires a fact ID')
            if op.kind == 'revert':
                payload = self.operations.payload(op)
                if payload is None:
                    state.pop(op.fact_id, None)
                else:
                    state[op.fact_id] = self._decode(canonical(payload))
            elif op.kind == 'invalidate':
                state.pop(op.fact_id, None)
            elif op.kind in ('add', 'update'):
                payload = self.operations.payload(op)
                if payload is not None:
                    state[op.fact_id] = self._decode(canonical(payload))
        return state

    def update(
        self,
        fact_id: str,
        text: str | None = None,
        *,
        valid_from: datetime | str | None = None,
        valid_to: datetime | str | None = None,
    ) -> Fact:
        with self._atomic():
            fact = next((f for f in self.recall() if f.id == fact_id), None)
            if fact is None:
                raise KeyError(fact_id)
            if text is not None and (not isinstance(text, str) or not text.strip()):
                raise ValueError('Fact text must be nonempty')
            valid = ValidInterval(
                valid_from or fact.valid_from or fact.created_at or self._event_time(),
                valid_to if valid_to is not None else fact.valid_to,
            )
            return self._save(
                replace(
                    fact,
                    text=text if text is not None else fact.text,
                    valid_from=valid.start.isoformat(),
                    valid_to=valid.end.isoformat() if valid.end else None,
                )
            )

    def timeline(self, head: str | None = None) -> Timeline:
        timeline = Timeline()
        chain = []
        cursor = self.head if head is None else head
        while cursor:
            op = self.operations.get(cursor)
            chain.append(op)
            cursor = op.parents[0] if op.parents else None

        def retire(fact_id: str | None, at: datetime, keep_past: bool = False) -> None:
            rows = []
            additions = []
            for old in timeline.rows:
                if old.transaction.end is not None or (
                    fact_id is not None and old.fact_id != fact_id
                ):
                    rows.append(old)
                    continue
                rows.append(
                    replace(old, transaction=TransactionInterval(old.transaction.start, at))
                )
                end = min(old.valid.end, at) if old.valid.end is not None else at
                if keep_past and old.valid.start < end:
                    additions.append(
                        TemporalVersion(
                            old.fact_id,
                            dict(old.payload),
                            ValidInterval(old.valid.start, end),
                            TransactionInterval(at),
                        )
                    )
            timeline.rows = rows + additions

        for op in reversed(chain):
            if self.is_purged(op.fact_id):
                continue
            at = timestamp(op.recorded_at)
            if op.kind in ('merge', 'restore'):
                retire(None, at)
                for fid, h in op.metadata['state'].items():
                    row = self.db.execute(
                        'SELECT payload FROM memory_blobs WHERE digest=?', (h,)
                    ).fetchone()
                    if row and (not self.is_purged(fid)):
                        payload = json.loads(row[0])
                        timeline.correct(
                            fid,
                            payload,
                            ValidInterval(payload['valid_from'], payload.get('valid_to')),
                            at,
                        )
            elif op.kind == 'invalidate':
                retire(op.fact_id, at, True)
            elif op.kind in ('add', 'update', 'revert'):
                if op.fact_id is None:
                    raise ValueError('Fact event requires a fact ID')
                payload = self.operations.payload(op)
                if payload is not None:
                    timeline.correct(
                        op.fact_id,
                        payload,
                        ValidInterval(payload['valid_from'], payload.get('valid_to')),
                        at,
                    )
                elif op.kind == 'revert':
                    retire(op.fact_id, at)
        timeline.rows = [v for v in timeline.rows if not self.is_purged(v.fact_id)]
        return timeline

    def invalidate(self, fact_id: str, *, reason: str = 'invalidated') -> str:
        with self._atomic():
            fact = next((f for f in self.recall() if f.id == fact_id), None)
            if fact is None:
                raise KeyError(fact_id)
            with self._atomic():
                from .operations import digest

                self._record(
                    'invalidate',
                    fact_id,
                    {'id': fact_id, 'reason': reason},
                    metadata={'reason_hash': digest(reason)},
                )
                self.db.execute('DELETE FROM facts WHERE id=?', (fact_id,))
                self.db.execute('DELETE FROM fact_anchors WHERE fact_id=?', (fact_id,))
            return fact_id

    def is_purged(self, fact_id: str | None) -> bool:
        return (
            fact_id is not None
            and self.db.execute(
                'SELECT 1 FROM memory_purged WHERE fact_id=?', (fact_id,)
            ).fetchone()
            is not None
        )

    def forget(self, fact_id: str) -> list[str]:
        with self._atomic():
            if self.is_purged(fact_id):
                forgotten = []
            else:
                known = self.db.execute(
                    "SELECT 1 FROM memory_operations WHERE json_extract(canonical,'$.fact_id')=?",
                    (fact_id,),
                ).fetchone()
                if not known:
                    raise KeyError(fact_id)
                forgotten = self._purge({fact_id, *self.dependents(fact_id)})
        self._physical_cleanup()
        return forgotten

    def replay_digest(self, head: str | None = None) -> str:
        from .operations import digest

        return digest({fid: asdict(f) for fid, f in sorted(self.replay(head).items())})

    def log(self, *, head: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        rows = [
            {
                **op.to_dict(),
                'payload': None if self.is_purged(op.fact_id) else self.operations.payload(op),
            }
            for op in reversed(self.operations.ancestry(head if head is not None else self.head))
        ]
        return rows[:limit] if limit is not None else rows

    def diff(self, left: str | None, right: str | None = None) -> dict[str, Any]:
        a, b = (
            self.replay(left) if left else {},
            self.replay(right if right is not None else self.head),
        )
        return {
            'added': {k: b[k].to_dict() for k in sorted(b.keys() - a.keys())},
            'removed': {k: a[k].to_dict() for k in sorted(a.keys() - b.keys())},
            'changed': {
                k: {'before': a[k].to_dict(), 'after': b[k].to_dict()}
                for k in sorted(a.keys() & b.keys())
                if a[k] != b[k]
            },
        }

    def _materialize(self, state: dict[str, Fact]) -> None:
        self.db.execute('DELETE FROM facts')
        self.db.execute('DELETE FROM fact_anchors')
        for fact in state.values():
            if self.is_purged(fact.id):
                continue
            self.db.execute('INSERT INTO facts VALUES (?,?)', (fact.id, canonical(asdict(fact))))
            self.db.executemany(
                'INSERT INTO fact_anchors VALUES (?,?,?)',
                [(fact.id, a.symbol_id, a.content_hash) for a in fact.anchors],
            )

    def revert(self, operation_id: str) -> str:
        with self._atomic():
            op = self.operations.get(operation_id)
            if any(
                o.metadata.get('reverts') == operation_id
                for o in self.operations.ancestry(self.head)
            ):
                raise ValueError('Operation was already reverted')
            if operation_id not in {o.id for o in self.operations.ancestry(self.head)}:
                raise ValueError('Operation is not on the active branch')
            if op.kind == 'merge':
                before = self.replay(op.parents[0]) if op.parents else {}
                with self._atomic():
                    inverse = self._snapshot('restore', before, metadata={'reverts': operation_id})
                    self._materialize(before)
                return inverse.id
            if op.kind not in ('add', 'update', 'invalidate'):
                raise ValueError('Operation kind is not reversible')
            if self.is_purged(op.fact_id):
                raise ValueError('Forgotten payloads cannot be restored')
            before = self.replay(op.parents[0]) if op.parents else {}
            if op.fact_id is None:
                raise ValueError('Fact event requires a fact ID')
            prior = before.get(op.fact_id)
            with self._atomic():
                inverse = self._record(
                    'revert',
                    op.fact_id,
                    asdict(prior) if prior else None,
                    metadata={'reverts': operation_id},
                )
                self._materialize(self.replay())
            return inverse.id

    def verify(self) -> bool:
        stored = {
            row[0]: self._decode(row[1]) for row in self.db.execute('SELECT id,payload FROM facts')
        }
        expected = self.replay()
        if stored != expected:
            raise ValueError('Materialized memory differs from verified operation replay')
        return True

    @property
    def current_branch(self) -> str:
        row = self.db.execute("SELECT value FROM memory_meta WHERE key='branch'").fetchone()
        if row is None or row[0] is None:
            raise ValueError('Missing active memory branch')
        return str(row[0])

    def branches(self) -> dict[str, str | None]:
        return dict(self.db.execute('SELECT name,head FROM memory_branches ORDER BY name'))

    def common_base(self, left: str | None, right: str | None) -> str | None:
        common = {o.id for o in self.operations.ancestry(left)} & {
            o.id for o in self.operations.ancestry(right)
        }
        if not common:
            return None
        candidates = []
        for oid in common:
            if not any(
                oid != other and oid in {a.id for a in self.operations.ancestry(other)}
                for other in common
            ):
                candidates.append(oid)
        if len(candidates) != 1:
            raise ValueError('Multiple merge bases require explicit resolution')
        return candidates[0]

    @staticmethod
    def _branch_name(name: str) -> str:
        if (
            not isinstance(name, str)
            or not name
            or any(c.isspace() or c in '~^:?*[' or c == chr(92) for c in name)
            or ('..' in name)
            or ('@{' in name)
            or name.startswith(('.', '/'))
            or name.endswith(('/', '.lock', '.'))
        ):
            raise ValueError('Invalid branch name')
        return name

    def branch(self, name: str, *, from_head: str | None = None) -> str | None:
        with self._atomic():
            name = self._branch_name(name)
            head = self.head if from_head is None else from_head or None
            if head:
                self.operations.get(head)
            with self._atomic():
                self.db.execute('INSERT INTO memory_branches VALUES (?,?)', (name, head))
            return head

    def switch(self, name: str) -> str | None:
        with self._atomic():
            row = self.db.execute(
                'SELECT head FROM memory_branches WHERE name=?', (name,)
            ).fetchone()
            if row is None:
                raise KeyError(name)
            with self._atomic():
                self.db.execute("UPDATE memory_meta SET value=? WHERE key='branch'", (name,))
                self.db.execute("UPDATE memory_meta SET value=? WHERE key='head'", (row[0],))
                self._materialize(self.replay(row[0]) if row[0] else {})
            return self.head

    def sync_git(self, repository: Path | str) -> str:
        with self._atomic():
            import subprocess

            result = subprocess.run(
                ['git', '-C', str(repository), 'symbolic-ref', '--quiet', '--short', 'HEAD'],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                name = result.stdout.strip()
            else:
                revision = subprocess.run(
                    ['git', '-C', str(repository), 'rev-parse', '--verify', 'HEAD'],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
                name = 'detached/' + revision
            if name not in self.branches():
                self.branch(name)
            self.switch(name)
            return name

    def rename_branch(self, old: str, new: str) -> str:
        with self._atomic():
            new = self._branch_name(new)
            if old not in self.branches():
                raise KeyError(old)
            with self._atomic():
                self.db.execute('UPDATE memory_branches SET name=? WHERE name=?', (new, old))
                if self.current_branch == old:
                    self.db.execute("UPDATE memory_meta SET value=? WHERE key='branch'", (new,))
            return new

    def delete_branch(self, name: str) -> None:
        with self._atomic():
            if name == self.current_branch:
                raise ValueError('Cannot delete the active branch')
            if name not in self.branches():
                raise KeyError(name)
            with self._atomic():
                self.db.execute('DELETE FROM memory_branches WHERE name=?', (name,))

    @staticmethod
    def _same_fact(left: Fact | None, right: Fact | None) -> bool:
        if left is None or right is None:
            return left is right
        return replace(left, recorded_at=None) == replace(right, recorded_at=None)

    def merge_preview(self, source: str) -> dict[str, Any]:
        if source not in self.branches():
            raise KeyError(source)
        source_head = self.branches()[source]
        base = self.common_base(self.head, source_head)
        ancestor = self.replay(base) if base else {}
        ours = self.replay(self.head) if self.head else {}
        theirs = self.replay(source_head) if source_head else {}
        state, conflicts = ({}, {})
        for fid in sorted(ancestor.keys() | ours.keys() | theirs.keys()):
            if self.is_purged(fid):
                continue
            a, o, t = (ancestor.get(fid), ours.get(fid), theirs.get(fid))
            if self._same_fact(o, t):
                selected = o
            elif self._same_fact(o, a):
                selected = t
            elif self._same_fact(t, a):
                selected = o
            else:
                conflicts[fid] = {
                    'base': a,
                    'ours': o,
                    'theirs': t,
                    'kind': 'delete_update' if o is None or t is None else 'concurrent_update',
                }
                continue
            if selected is not None:
                state[fid] = selected
        return {'base': base, 'state': state, 'conflicts': conflicts, 'source_head': source_head}

    def _snapshot(
        self,
        kind: str,
        state: dict[str, Fact],
        *,
        metadata: dict[str, Any] | None = None,
        parents: Iterable[str] | None = None,
    ) -> Operation:
        from .operations import digest

        references = {}
        for fid, fact in state.items():
            if self.is_purged(fid):
                continue
            payload = asdict(fact)
            h = digest(payload)
            self.db.execute(
                'INSERT OR IGNORE INTO memory_blobs VALUES (?,?)', (h, canonical(payload))
            )
            references[fid] = h
        return self._record(
            kind, metadata={**(metadata or {}), 'state': references}, parents=parents
        )

    def merge(self, source: str, *, resolutions: dict[str, str] | None = None) -> str:
        with self._atomic():
            preview = self.merge_preview(source)
            resolutions = resolutions or {}
            unresolved = {
                fid: c for fid, c in preview['conflicts'].items() if fid not in resolutions
            }
            if unresolved:
                raise MergeConflict(unresolved)
            if set(resolutions) - set(preview['conflicts']):
                raise ValueError('Resolution supplied for a non-conflicting fact')
            for fid, choice in resolutions.items():
                if choice not in ('ours', 'theirs', 'base', 'delete'):
                    raise ValueError('Resolution must be ours, theirs, base or delete')
                selected = None if choice == 'delete' else preview['conflicts'][fid][choice]
                if selected is not None:
                    preview['state'][fid] = selected
            with self._atomic():
                op = self._snapshot(
                    'merge',
                    preview['state'],
                    metadata={
                        'source': source,
                        'base': preview['base'],
                        'resolutions': resolutions,
                    },
                    parents=tuple(
                        dict.fromkeys(h for h in (self.head, preview['source_head']) if h)
                    ),
                )
                self._materialize(preview['state'])
            return op.id

    def _validate_derivations(self, derived_id: str, sources: Iterable[str]) -> None:
        known = {f.id for f in self.recall()}
        for source_id in sources:
            if source_id not in known or self.is_purged(source_id):
                raise ValueError('Derivation source is unavailable')
            seen = set()
            stack = [derived_id]
            while stack:
                node = stack.pop()
                if node == source_id:
                    raise ValueError('Derivation cycle')
                if node in seen:
                    continue
                seen.add(node)
                stack.extend(
                    r[0]
                    for r in self.db.execute(
                        'SELECT derived_id FROM memory_derivations WHERE source_id=?', (node,)
                    )
                )

    def add_derivations(self, fact_id: str, sources: Iterable[str]) -> Fact:
        with self._atomic():
            fact = next((f for f in self.recall() if f.id == fact_id), None)
            if fact is None:
                raise KeyError(fact_id)
            sources = tuple(dict.fromkeys((*fact.derived_from, *sources)))
            self._validate_derivations(fact_id, sources)
            with self._atomic():
                updated = self._save(replace(fact, derived_from=sources))
                self.db.executemany(
                    'INSERT OR IGNORE INTO memory_derivations VALUES (?,?)',
                    [(source_id, fact_id) for source_id in sources],
                )
            return updated

    def dependents(self, fact_id: str) -> list[str]:
        seen = set()
        stack = [fact_id]
        while stack:
            source_id = stack.pop()
            for (derived_id,) in self.db.execute(
                'SELECT derived_id FROM memory_derivations WHERE source_id=?', (source_id,)
            ):
                if derived_id not in seen:
                    seen.add(derived_id)
                    stack.append(derived_id)
        return sorted(seen - {fact_id})

    def _purge(self, fact_ids: set[str]) -> list[str]:
        forgotten = sorted(fid for fid in fact_ids if not self.is_purged(fid))
        with self._atomic():
            for fid in forgotten:
                self.db.execute('INSERT OR IGNORE INTO memory_purged VALUES (?)', (fid,))
                self.db.execute(
                    "DELETE FROM memory_blobs WHERE json_extract(payload,'$.id')=?", (fid,)
                )
                self.db.execute('DELETE FROM facts WHERE id=?', (fid,))
                self.db.execute('DELETE FROM fact_anchors WHERE fact_id=?', (fid,))
                self.db.execute('DELETE FROM fact_audit WHERE fact_id=?', (fid,))
                self.db.execute(
                    'DELETE FROM conflict_audit WHERE fact_id=? OR winner_id=? OR EXISTS (SELECT 1 FROM json_each(candidate_ids) WHERE value=?)',
                    (fid, fid, fid),
                )
                self._record('forget', fid)
        return forgotten

    def forget_by(self, *, session: str | None = None, source: str | None = None) -> list[str]:
        if session is None and source is None:
            raise ValueError('Specify session or source')
        with self._atomic():
            selected: set[str] = set()
            for (payload,) in self.db.execute('SELECT payload FROM memory_blobs'):
                data = json.loads(payload)
                if (
                    'id' in data
                    and (session is None or data.get('session') == session)
                    and (source is None or data.get('source') == source)
                ):
                    selected.add(str(data['id']))
            ids = set(selected)
            for fid in selected:
                ids.update(self.dependents(fid))
            forgotten = self._purge(ids)
        self._physical_cleanup()
        return forgotten

    @contextmanager
    def _atomic(self) -> Iterator[None]:
        nested = self.db.in_transaction
        token = ''
        if nested:
            self._savepoint_seq += 1
            token = 'memory_' + str(self._savepoint_seq)
            self.db.execute('SAVEPOINT ' + token)
        else:
            self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
        except BaseException:
            if nested:
                self.db.execute('ROLLBACK TO SAVEPOINT ' + token)
                self.db.execute('RELEASE SAVEPOINT ' + token)
            else:
                self.db.rollback()
            raise
        else:
            if nested:
                self.db.execute('RELEASE SAVEPOINT ' + token)
            else:
                self.db.commit()

    def _physical_cleanup(self) -> None:
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.db.execute('VACUUM')
