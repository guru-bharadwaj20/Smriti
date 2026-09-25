"""Filesystem events feed deterministic incremental indexing jobs."""
from pathlib import Path
from collections import deque
from threading import Lock
from time import monotonic
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from smriti.merkle import FileChange


class ChangeWatcher:
    def __init__(self, root: str | Path, debounce_seconds: float = 0.1):
        self.root = Path(root).resolve()
        if debounce_seconds < 0:
            raise ValueError("Debounce interval must be nonnegative")
        self.debounce_seconds = debounce_seconds
        self.pending = {}
        self.lock = Lock()
        self.observer = None

    def feed(self, kind: str, path: str, old_path: str | None = None) -> None:
        with self.lock:
            if path.startswith(".git/"):
                if path in {".git/HEAD", ".git/index"} or path.startswith(".git/refs/"):
                    self.pending["@checkout"] = (monotonic(), FileChange("rescan", ""))
                return
            if any(part in {".smriti", ".venv", "__pycache__"} for part in Path(path).parts):
                return
            self.pending[path] = (monotonic(), FileChange(kind, path, old_path))

    def poll(self, *, now: float | None = None, force: bool = False) -> list[FileChange]:
        now = monotonic() if now is None else now
        with self.lock:
            ready = [path for path, (timestamp, event) in self.pending.items()
                     if force or now - timestamp >= self.debounce_seconds]
            events = [self.pending.pop(path)[1] for path in sorted(ready)]
        return [FileChange("rescan", "")] if any(event.kind == "rescan" for event in events) else events

    def start(self) -> None:
        watcher = self
        class Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                if event.is_directory or event.event_type not in {"created", "modified", "deleted", "moved"}:
                    return
                try:
                    source = Path(event.src_path).relative_to(watcher.root).as_posix()
                    destination = Path(event.dest_path).relative_to(watcher.root).as_posix() if event.event_type == "moved" else source
                except ValueError:
                    return
                watcher.feed(event.event_type, destination, source if event.event_type == "moved" else None)
        if self.observer is not None:
            raise RuntimeError("Watcher already started")
        self.observer = Observer()
        self.observer.schedule(Handler(), str(self.root), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=5)
            if self.observer.is_alive():
                raise TimeoutError("Filesystem observer failed to stop")
            self.observer = None


def affected_file_jobs(events: list[FileChange]) -> tuple[list[str], list[str], bool]:
    """A checkout requires one snapshot diff; source paths queue once per burst."""
    if any(event.kind == "rescan" for event in events):
        return [], [], True
    parse, remove = set(), set()
    for event in events:
        if event.kind in {"created", "modified", "moved"}:
            parse.add(event.path)
        if event.kind == "deleted":
            remove.add(event.path)
        if event.kind == "moved" and event.old_path:
            remove.add(event.old_path)
    return sorted(parse), sorted(remove - parse), False


from dataclasses import dataclass, replace
from smriti.models import Symbol, Edge


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
    return SymbolDelta([after[key] for key in sorted(after.keys() - before.keys())],
        [after[key] for key in sorted(common) if before[key] != after[key]],
        [before[key] for key in sorted(before.keys() - after.keys())],
        [after[key] for key in sorted(common) if before[key] == after[key]], [])


def structural_fingerprint(symbol: Symbol) -> str:
    """A rename must preserve a unique AST body, not merely a similar name."""
    import ast
    import textwrap
    from hashlib import sha256
    try:
        tree = ast.parse(textwrap.dedent(symbol.body))
        if len(tree.body) == 1 and isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            tree.body[0].name = "@renamed"
        content = ast.dump(tree, include_attributes=False)
    except SyntaxError:
        content = symbol.body
    return sha256((symbol.kind + "\0" + content).encode()).hexdigest()


def preserve_symbol_ids(old: list[Symbol], new: list[Symbol]) -> tuple[list[Symbol], dict[str, str]]:
    before, after = {s.id: s for s in old}, {s.id: s for s in new}
    removed = [s for s in old if s.id not in after]
    added = [s for s in new if s.id not in before]
    mapping = {}
    fingerprints = {structural_fingerprint(s) for s in removed}
    for fingerprint in fingerprints:
        sources = [s for s in removed if structural_fingerprint(s) == fingerprint]
        targets = [s for s in added if structural_fingerprint(s) == fingerprint]
        if len(sources) == len(targets) == 1:
            mapping[targets[0].id] = sources[0].id
    renamed = [replace(s, id=mapping.get(s.id, s.id), parent_id=mapping.get(s.parent_id, s.parent_id)) for s in new]
    return renamed, mapping


def prune_edges(edges: list[Edge], removed_ids: set[str]) -> list[Edge]:
    """Remove both incoming and outgoing references to deleted symbols."""
    return [edge for edge in edges if edge.source not in removed_ids and edge.target not in removed_ids]


def update_search_indexes(delta: SymbolDelta, *, lexical_upsert, lexical_delete,
                          vector_upsert, vector_delete) -> None:
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


def apply_file_symbols(current: list[Symbol], replacements: dict[str, list[Symbol]],
                       deleted_paths: set[str] = frozenset()) -> list[Symbol]:
    """Replace affected files only; stable ordering agrees with a full scan."""
    changed_paths = replacements.keys() | deleted_paths
    result = [symbol for symbol in current if symbol.path not in changed_paths]
    result.extend(symbol for symbols in replacements.values() for symbol in symbols)
    return sorted(result, key=lambda s: (s.path, s.start_byte, s.qualname))
