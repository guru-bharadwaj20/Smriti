
"""Content-addressed operations reference purgeable payload blobs."""
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
# P10.09
def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Operation:
    kind: str
    fact_id: str | None
    payload_hash: str | None
    parents: tuple[str, ...]
    recorded_at: str
    metadata: dict

    @property
    def id(self):
        return digest(asdict(self))

    def to_dict(self):
        return {"id": self.id, **asdict(self)}
# P10.10
class OperationLog:
    def __init__(self, connection):
        self.db = connection
        self.db.execute("CREATE TABLE IF NOT EXISTS memory_operations (seq INTEGER PRIMARY KEY, oid TEXT UNIQUE NOT NULL, canonical TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS memory_blobs (digest TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.db.commit()

    def get(self, oid):
        row = self.db.execute("SELECT canonical FROM memory_operations WHERE oid=?", (oid,)).fetchone()
        if row is None:
            raise KeyError(oid)
        data = json.loads(row[0])
        data["parents"] = tuple(data["parents"])
        op = Operation(**data)
        if op.id != oid:
            raise ValueError("Operation hash mismatch")
        return op

    def append_uncommitted(self, kind, fact_id=None, payload=None, *, parents=(), recorded_at=None, metadata=None):
        for parent in parents:
            self.get(parent)
        recorded_at = recorded_at or datetime.now(timezone.utc).isoformat()
        payload_hash = digest(payload) if payload is not None else None
        op = Operation(kind, fact_id, payload_hash, tuple(parents), recorded_at, metadata or {})
        if payload is not None:
            self.db.execute("INSERT OR IGNORE INTO memory_blobs VALUES (?,?)", (payload_hash, canonical(payload)))
        self.db.execute("INSERT OR IGNORE INTO memory_operations(oid,canonical) VALUES (?,?)", (op.id, canonical(asdict(op))))
        return op

    def append(self, *args, **kwargs):
        with self.db:
            return self.append_uncommitted(*args, **kwargs)

    def payload(self, operation):
        if operation.payload_hash is None:
            return None
        row = self.db.execute("SELECT payload FROM memory_blobs WHERE digest=?", (operation.payload_hash,)).fetchone()
        return json.loads(row[0]) if row else None

    def ancestry(self, head):
        seen = set()
        stack = [head] if head else []
        while stack:
            oid = stack.pop()
            if oid in seen:
                continue
            op = self.get(oid)
            seen.add(oid)
            stack.extend(op.parents)
        ordered = [self.get(oid) for (oid,) in self.db.execute("SELECT oid FROM memory_operations ORDER BY seq") if oid in seen]
        return ordered
# P10.11
