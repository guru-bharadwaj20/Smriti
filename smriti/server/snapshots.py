"""SQLite WAL-backed immutable query snapshots."""

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sqlite3
from types import MappingProxyType
from typing import cast

from smriti.models import Edge, Symbol


@dataclass(frozen=True)
class IndexSnapshot:
    version: int
    symbols: tuple[Symbol, ...]
    edges: tuple[Edge, ...]
    files: Mapping[str, str]


class ConcurrentUpdateError(RuntimeError):
    """A writer based on an obsolete snapshot must retry from a fresh view."""


class IndexStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value INTEGER);
                INSERT OR IGNORE INTO metadata VALUES ('version', 0);
                CREATE TABLE IF NOT EXISTS symbols (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS edges (source TEXT, target TEXT, kind TEXT, confidence REAL,
                    PRIMARY KEY(source, target, kind));
                CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, digest TEXT NOT NULL);
            ''')

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute('PRAGMA busy_timeout=30000')
        return connection

    def load(self) -> IndexSnapshot:
        connection = self._connect()
        try:
            connection.execute('BEGIN')
            version = int(connection.execute("SELECT value FROM metadata WHERE key='version'").fetchone()[0])
            symbols = tuple(Symbol(**json.loads(row[0])) for row in connection.execute('SELECT payload FROM symbols ORDER BY id'))
            edges = tuple(Edge(*row) for row in connection.execute('SELECT source,target,kind,confidence FROM edges ORDER BY source,target,kind'))
            files = dict(connection.execute('SELECT path,digest FROM files ORDER BY path'))
            connection.commit()
            return IndexSnapshot(version, symbols, edges, MappingProxyType(files))
        finally:
            connection.close()

    def publish(self, symbols: Iterable[Symbol], edges: Iterable[Edge],
                files: Mapping[str, str], *, expected_version: int) -> int:
        new_symbols = {symbol.id: json.dumps(asdict(symbol), sort_keys=True) for symbol in symbols}
        new_edges = {(edge.source, edge.target, edge.kind): edge.confidence for edge in edges}
        if any(source not in new_symbols or target not in new_symbols for source, target, _ in new_edges):
            raise ValueError('Graph edge has a missing symbol endpoint')
        connection = self._connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            current = int(connection.execute("SELECT value FROM metadata WHERE key='version'").fetchone()[0])
            if current != expected_version:
                raise ConcurrentUpdateError('Index changed while this writer was preparing its update')
            old_symbols = dict(connection.execute('SELECT id,payload FROM symbols'))
            for identity in old_symbols.keys() - new_symbols.keys():
                connection.execute('DELETE FROM symbols WHERE id=?', (identity,))
            for identity, payload in new_symbols.items():
                if old_symbols.get(identity) != payload:
                    connection.execute('INSERT OR REPLACE INTO symbols VALUES (?,?)', (identity, payload))
            old_edges = {(row[0], row[1], row[2]): row[3] for row in connection.execute('SELECT source,target,kind,confidence FROM edges')}
            for key in old_edges.keys() - new_edges.keys():
                connection.execute('DELETE FROM edges WHERE source=? AND target=? AND kind=?', key)
            for key, confidence in new_edges.items():
                if old_edges.get(key) != confidence:
                    connection.execute('INSERT OR REPLACE INTO edges VALUES (?,?,?,?)', (*key, confidence))
            old_files = dict(connection.execute('SELECT path,digest FROM files'))
            for path in old_files.keys() - files.keys():
                connection.execute('DELETE FROM files WHERE path=?', (path,))
            for path, digest in files.items():
                if old_files.get(path) != digest:
                    connection.execute('INSERT OR REPLACE INTO files VALUES (?,?)', (path, digest))
            version = current + 1
            connection.execute("UPDATE metadata SET value=? WHERE key='version'", (version,))
            connection.commit()
            return version
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
