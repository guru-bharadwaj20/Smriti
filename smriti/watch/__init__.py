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
