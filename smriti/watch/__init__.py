"""Filesystem events feed deterministic incremental indexing jobs."""
from pathlib import Path
from collections import deque
from threading import Lock
from time import monotonic
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from smriti.merkle import FileChange


class ChangeWatcher:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.queue = deque()
        self.lock = Lock()
        self.observer = None

    def feed(self, kind: str, path: str, old_path: str | None = None) -> None:
        with self.lock:
            self.queue.append(FileChange(kind, path, old_path))

    def poll(self) -> list[FileChange]:
        with self.lock:
            events = list(self.queue)
            self.queue.clear()
        return events

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
