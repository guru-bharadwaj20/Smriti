"""Durable, repository-local facts for coding agents."""
from dataclasses import dataclass, asdict
import json
import sqlite3
import uuid
import math


@dataclass(frozen=True)
class Fact:
    id: str
    text: str
    user: str | None = None
    session: str | None = None
    tool: str | None = None
    source: str | None = None
    confidence: float = 1.0


class MemoryStore:
    """SQLite-backed fact store. Each write is atomic and survives restart."""

    def __init__(self, db_path):
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def remember(self, text: str, *, fact_id=None, user=None, session=None, tool=None, source=None, confidence=1.0) -> Fact:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Fact text must be nonempty")
        if not isinstance(confidence, (float, int)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Confidence must be finite in [0, 1]")
        for value in (user, session, tool, source):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError("Provenance values must be nonempty strings")
        fact = Fact(fact_id or uuid.uuid4().hex, text, user, session, tool, source, float(confidence))
        with self.db:
            self.db.execute("INSERT INTO facts VALUES (?, ?)", (fact.id, json.dumps(asdict(fact))))
        return fact

    def recall(self, query="") -> list[Fact]:
        facts = [Fact(**json.loads(row[0])) for row in self.db.execute("SELECT payload FROM facts ORDER BY id")]
        return [f for f in facts if query.casefold() in f.text.casefold()]
