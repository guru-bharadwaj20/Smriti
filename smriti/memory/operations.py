"""Content-addressed operations reference purgeable payload blobs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Operation:
    kind: str
    fact_id: str | None
    payload_hash: str | None
    parents: tuple[str, ...]
    recorded_at: str
    metadata: dict[str, Any]

    @property
    def id(self) -> str:
        return digest(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {'id': self.id, **asdict(self)}


class OperationLog:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.db = connection
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS memory_operations (seq INTEGER PRIMARY KEY, oid TEXT UNIQUE NOT NULL, canonical TEXT NOT NULL)'
        )
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS memory_blobs (digest TEXT PRIMARY KEY, payload TEXT NOT NULL)'
        )
        self.db.commit()

    def get(self, oid: str) -> Operation:
        row = self.db.execute(
            'SELECT canonical FROM memory_operations WHERE oid=?', (oid,)
        ).fetchone()
        if row is None:
            raise KeyError(oid)
        data = json.loads(row[0])
        data['parents'] = tuple(data['parents'])
        op = Operation(**data)
        if op.id != oid:
            raise ValueError('Operation hash mismatch')
        return op

    def append_uncommitted(
        self,
        kind: str,
        fact_id: str | None = None,
        payload: dict[str, Any] | None = None,
        *,
        parents: tuple[str, ...] | list[str] = (),
        recorded_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Operation:
        for parent in parents:
            self.get(parent)
        recorded_at = recorded_at or datetime.now(UTC).isoformat()
        payload_hash = digest(payload) if payload is not None else None
        op = Operation(kind, fact_id, payload_hash, tuple(parents), recorded_at, metadata or {})
        if payload is not None:
            self.db.execute(
                'INSERT OR IGNORE INTO memory_blobs VALUES (?,?)',
                (payload_hash, canonical(payload)),
            )
        self.db.execute(
            'INSERT OR IGNORE INTO memory_operations(oid,canonical) VALUES (?,?)',
            (op.id, canonical(asdict(op))),
        )
        return op

    def append(self, *args: Any, **kwargs: Any) -> Operation:
        with self.db:
            return self.append_uncommitted(*args, **kwargs)

    def payload(self, operation: Operation) -> dict[str, Any] | None:
        if operation.payload_hash is None:
            return None
        row = self.db.execute(
            'SELECT payload FROM memory_blobs WHERE digest=?', (operation.payload_hash,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def ancestry(self, head: str | None) -> list[Operation]:
        seen = set()
        stack = [head] if head else []
        while stack:
            oid = stack.pop()
            if oid in seen:
                continue
            op = self.get(oid)
            seen.add(oid)
            stack.extend(op.parents)
        ordered = [
            self.get(oid)
            for (oid,) in self.db.execute('SELECT oid FROM memory_operations ORDER BY seq')
            if oid in seen
        ]
        return ordered
