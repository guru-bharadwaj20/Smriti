"""Durable, repository-local facts for coding agents."""
from dataclasses import dataclass, asdict, replace
import json
import sqlite3
import uuid
import math


@dataclass(frozen=True)
class Anchor:
    symbol_id: str
    content_hash: str = ""


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

    @property
    def scope(self):
        return 'symbol' if self.anchors else 'project'


class MemoryStore:
    """SQLite-backed fact store. Each write is atomic and survives restart."""

    def __init__(self, db_path):
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.db.execute('CREATE TABLE IF NOT EXISTS fact_anchors (fact_id TEXT, symbol_id TEXT, content_hash TEXT, PRIMARY KEY (fact_id, symbol_id))')
        self.db.commit()

    def close(self):
        self.db.close()

    def remember(self, text: str, *, fact_id=None, user=None, session=None, tool=None, source=None, confidence=1.0, anchors=(), selected_context=()) -> Fact:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Fact text must be nonempty")
        if not isinstance(confidence, (float, int)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Confidence must be finite in [0, 1]")
        for value in (user, session, tool, source):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError("Provenance values must be nonempty strings")
        if not anchors:
            anchors = tuple(Anchor(s['symbol_id'], s['content_hash']) if isinstance(s, dict) else Anchor(s.id, s.content_hash) for s in selected_context)
        anchors = tuple(Anchor(**a) if isinstance(a, dict) else a for a in anchors)
        if any(not isinstance(a, Anchor) or not a.symbol_id for a in anchors):
            raise ValueError("Anchors require symbol IDs")
        if any(not a.content_hash or not isinstance(a.content_hash, str) for a in anchors):
            raise ValueError("Anchors require content hashes")
        fact = Fact(fact_id or uuid.uuid4().hex, text, user, session, tool, source, float(confidence), anchors)
        with self.db:
            self.db.execute("INSERT INTO facts VALUES (?, ?)", (fact.id, json.dumps(asdict(fact))))
            self.db.executemany('INSERT INTO fact_anchors VALUES (?, ?, ?)', [(fact.id, a.symbol_id, a.content_hash) for a in anchors])
        return fact

    def recall(self, query="") -> list[Fact]:
        facts = [self._decode(row[0]) for row in self.db.execute("SELECT payload FROM facts ORDER BY id")]
        return [f for f in facts if query.casefold() in f.text.casefold()]

    @staticmethod
    def _decode(payload):
        data = json.loads(payload)
        data["anchors"] = tuple(Anchor(**a) for a in data.get("anchors", ()))
        return Fact(**data)

# P09.05

# P09.06

# P09.07

# P09.08
    def _save(self, fact):
        with self.db:
            self.db.execute("UPDATE facts SET payload=? WHERE id=?", (json.dumps(asdict(fact)), fact.id))
        return fact

    def refresh(self, symbols, *, renames=None, commit=None):
        """symbols maps stable symbol IDs to current content hashes."""
        renames = renames or {}
        changes = []
        for fact in self.recall():
            moved = tuple(Anchor(renames[a.symbol_id], a.content_hash) if a.symbol_id in renames and symbols.get(renames[a.symbol_id]) == a.content_hash else a for a in fact.anchors)
            if moved != fact.anchors:
                fact = self._save(replace(fact, anchors=moved))
                changes.append(fact)
            if any(a.symbol_id not in symbols for a in fact.anchors):
                changes.append(self._save(replace(fact, freshness='orphaned', freshness_reason='anchor_deleted', triggering_commit=commit)))
            elif any(a.symbol_id in symbols and symbols[a.symbol_id] != a.content_hash for a in fact.anchors):
                changes.append(self._save(replace(fact, freshness="stale", freshness_reason="anchor_changed", triggering_commit=commit)))
        return changes
# P09.09

# P09.10

# P09.11

# P09.12
