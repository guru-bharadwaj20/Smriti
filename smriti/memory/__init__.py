"""Durable, repository-local facts for coding agents."""
from dataclasses import dataclass, asdict
import json
import sqlite3
import uuid


@dataclass(frozen=True)
class Fact:
    id: str
    text: str


class MemoryStore:
    """SQLite-backed fact store. Each write is atomic and survives restart."""

    def __init__(self, db_path):
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def remember(self, text: str, *, fact_id=None) -> Fact:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Fact text must be nonempty")
        fact = Fact(fact_id or uuid.uuid4().hex, text)
        with self.db:
            self.db.execute("INSERT INTO facts VALUES (?, ?)", (fact.id, json.dumps(asdict(fact))))
        return fact

    def recall(self, query="") -> list[Fact]:
        facts = [Fact(**json.loads(row[0])) for row in self.db.execute("SELECT payload FROM facts ORDER BY id")]
        return [f for f in facts if query.casefold() in f.text.casefold()]
