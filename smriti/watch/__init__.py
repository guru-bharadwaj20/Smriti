"""Filesystem events feed deterministic incremental indexing jobs."""

import os
from collections.abc import Callable
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from threading import Lock
from time import monotonic

from watchdog.events import FileSystemEvent, FileSystemEventHandler, FileSystemMovedEvent
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from smriti.merkle import FileChange, MerkleSnapshot, hash_content, hash_directory, hash_file
from smriti.models import Edge, Symbol


class ChangeWatcher:
    def __init__(self, root: str | Path, debounce_seconds: float = 0.1) -> None:
        self.root = Path(root).resolve()
        if debounce_seconds < 0:
            raise ValueError('Debounce interval must be nonnegative')
        self.debounce_seconds = debounce_seconds
        self.pending: dict[str, tuple[float, FileChange]] = {}
        self.lock = Lock()
        self.observer: BaseObserver | None = None

    def feed(self, kind: str, path: str, old_path: str | None = None) -> None:
        with self.lock:
            if path.startswith('.git/'):
                if path in {'.git/HEAD', '.git/index'} or path.startswith('.git/refs/'):
                    self.pending['@checkout'] = (monotonic(), FileChange('rescan', ''))
                return
            if any(part in {'.smriti', '.venv', '__pycache__'} for part in Path(path).parts):
                return
            self.pending[path] = (monotonic(), FileChange(kind, path, old_path))

    def poll(self, *, now: float | None = None, force: bool = False) -> list[FileChange]:
        now = monotonic() if now is None else now
        with self.lock:
            ready = [
                path
                for path, (timestamp, event) in self.pending.items()
                if force or now - timestamp >= self.debounce_seconds
            ]
            events = [self.pending.pop(path)[1] for path in sorted(ready)]
        return (
            [FileChange('rescan', '')]
            if any(event.kind == 'rescan' for event in events)
            else events
        )

    def start(self) -> None:
        watcher = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event: FileSystemEvent) -> None:
                if event.is_directory or event.event_type not in {
                    'created',
                    'modified',
                    'deleted',
                    'moved',
                }:
                    return
                try:
                    source = Path(os.fsdecode(event.src_path)).relative_to(watcher.root).as_posix()
                    destination = (
                        Path(os.fsdecode(event.dest_path)).relative_to(watcher.root).as_posix()
                        if isinstance(event, FileSystemMovedEvent)
                        else source
                    )
                except ValueError:
                    return
                watcher.feed(
                    event.event_type, destination, source if event.event_type == 'moved' else None
                )

        if self.observer is not None:
            raise RuntimeError('Watcher already started')
        self.observer = Observer()
        self.observer.schedule(Handler(), str(self.root), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5)
            if self.observer.is_alive():
                raise TimeoutError('Filesystem observer failed to stop')
            self.observer = None


def affected_file_jobs(events: list[FileChange]) -> tuple[list[str], list[str], bool]:
    """A checkout requires one snapshot diff; source paths queue once per burst."""
    if any(event.kind == 'rescan' for event in events):
        return [], [], True
    parse: set[str] = set()
    remove: set[str] = set()
    for event in events:
        if event.kind in {'created', 'modified', 'moved'}:
            parse.add(event.path)
        if event.kind == 'deleted':
            remove.add(event.path)
        if event.kind == 'moved' and event.old_path:
            remove.add(event.old_path)
    return sorted(parse), sorted(remove - parse), False


@dataclass
class SymbolDelta:
    added: list[Symbol]
    changed: list[Symbol]
    removed: list[Symbol]
    unchanged: list[Symbol]
    renames: list[tuple[str, str]]


def diff_symbols(old: list[Symbol], new: list[Symbol]) -> SymbolDelta:
    before, after = {s.id: s for s in old}, {s.id: s for s in new}
    common = before.keys() & after.keys()
    return SymbolDelta(
        [after[key] for key in sorted(after.keys() - before.keys())],
        [after[key] for key in sorted(common) if before[key] != after[key]],
        [before[key] for key in sorted(before.keys() - after.keys())],
        [after[key] for key in sorted(common) if before[key] == after[key]],
        [],
    )


def structural_fingerprint(symbol: Symbol) -> str:
    """A rename must preserve a unique AST body, not merely a similar name."""
    import ast
    import textwrap
    from hashlib import sha256

    try:
        tree = ast.parse(textwrap.dedent(symbol.body))
        if len(tree.body) == 1 and isinstance(
            tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            tree.body[0].name = '@renamed'
        content = ast.dump(tree, include_attributes=False)
    except SyntaxError:
        content = symbol.body
    return sha256((symbol.kind + '\0' + content).encode()).hexdigest()


def preserve_symbol_ids(
    old: list[Symbol], new: list[Symbol]
) -> tuple[list[Symbol], dict[str, str]]:
    before, after = {s.id: s for s in old}, {s.id: s for s in new}
    removed = [s for s in old if s.id not in after]
    added = [s for s in new if s.id not in before]
    mapping: dict[str, str] = {}
    fingerprints = {structural_fingerprint(s) for s in removed}
    for fingerprint in fingerprints:
        sources = [s for s in removed if structural_fingerprint(s) == fingerprint]
        targets = [s for s in added if structural_fingerprint(s) == fingerprint]
        if len(sources) == len(targets) == 1:
            mapping[targets[0].id] = sources[0].id
    renamed = [
        replace(
            s,
            id=mapping.get(s.id, s.id),
            parent_id=mapping.get(s.parent_id, s.parent_id) if s.parent_id else None,
        )
        for s in new
    ]
    return renamed, mapping


def prune_edges(edges: list[Edge], removed_ids: set[str]) -> list[Edge]:
    """Remove both incoming and outgoing references to deleted symbols."""
    return [
        edge for edge in edges if edge.source not in removed_ids and edge.target not in removed_ids
    ]


def update_search_indexes(
    delta: SymbolDelta,
    *,
    lexical_upsert: Callable[[Symbol], None],
    lexical_delete: Callable[[str], None],
    vector_upsert: Callable[[Symbol], None],
    vector_delete: Callable[[str], None],
) -> None:
    """Run both index adapters for exactly the affected IDs.

    The caller must stage these callbacks in its atomic generation transaction.
    Identical symbols are never embedded again. A callback failure propagates.
    """
    for symbol in delta.removed:
        lexical_delete(symbol.id)
        vector_delete(symbol.id)
    for symbol in [*delta.added, *delta.changed]:
        lexical_upsert(symbol)
        vector_upsert(symbol)


def apply_file_symbols(
    current: list[Symbol],
    replacements: dict[str, list[Symbol]],
    deleted_paths: AbstractSet[str] = frozenset(),
) -> list[Symbol]:
    """Replace affected files only; stable ordering agrees with a full scan."""
    changed_paths = replacements.keys() | deleted_paths
    result = [symbol for symbol in current if symbol.path not in changed_paths]
    result.extend(symbol for symbols in replacements.values() for symbol in symbols)
    return sorted(result, key=lambda s: (s.path, s.start_byte, s.qualname))


def refresh_snapshot(root: str | Path, old: MerkleSnapshot, paths: list[str]) -> MerkleSnapshot:
    """Read only affected leaves, rebuilding their ancestor hashes bottom-up."""
    import os

    root = Path(root).resolve()
    snapshot = MerkleSnapshot(dict(old.files), dict(old.directories))
    affected = {''}
    for name in paths:
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Expected repository-relative file path')
        path = root / name
        if not path.parent.resolve().is_relative_to(root):
            raise ValueError('Path traverses an external symlink')
        if path.is_symlink():
            snapshot.files[name] = hash_content(b'symlink\0' + os.fsencode(os.readlink(path)))
        elif path.is_file():
            snapshot.files[name] = hash_file(path)
        else:
            snapshot.files.pop(name, None)
        for parent in relative.parents:
            affected.add('' if str(parent) == '.' else parent.as_posix())
    for directory in sorted(affected, key=lambda p: (p.count('/') + bool(p), p), reverse=True):
        target = root / directory
        if directory and not target.is_dir():
            snapshot.directories.pop(directory, None)
            continue
        children = {}
        for leaf_name, digest in snapshot.files.items():
            parent_name = PurePosixPath(leaf_name).parent.as_posix()
            if ('' if parent_name == '.' else parent_name) == directory:
                children[PurePosixPath(leaf_name).name] = digest
        for leaf_name, digest in snapshot.directories.items():
            if not leaf_name or leaf_name == directory:
                continue
            parent_name = PurePosixPath(leaf_name).parent.as_posix()
            if ('' if parent_name == '.' else parent_name) == directory:
                children[PurePosixPath(leaf_name).name] = digest
        snapshot.directories[directory] = hash_directory(children)
    return snapshot


def measure_incremental_update(root: str | Path, path: str, repeats: int = 31) -> dict[str, object]:
    import os
    import platform
    import statistics
    from time import perf_counter

    from smriti.merkle import RepositoryScanner
    from smriti.parse import SourceParser

    root = Path(root)
    source = (root / path).read_bytes()
    scanner, parser = RepositoryScanner(), SourceParser()
    snapshot = scanner.scan(root)
    parser.parse(path, source)
    timings = []
    try:
        for index in range(repeats):
            edited = source.replace(b'return 0', f'return {index + 1}'.encode())
            (root / path).write_bytes(edited)
            started = perf_counter()
            snapshot = refresh_snapshot(root, snapshot, [path])
            parser.parse(path, edited)
            timings.append((perf_counter() - started) * 1000)
            if snapshot != scanner.scan(root):
                raise AssertionError('Incremental and fresh snapshots differ')
    finally:
        (root / path).write_bytes(source)
    return {
        'files': len(snapshot.files),
        'repeats': repeats,
        'p50_ms': statistics.median(timings),
        'p95_ms': sorted(timings)[max(0, int(len(timings) * 0.95) - 1)],
        'cpu': platform.processor(),
        'cpu_count': os.cpu_count(),
        'os': platform.platform(),
        'python': platform.python_version(),
        'samples_ms': timings,
    }
