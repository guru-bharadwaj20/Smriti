"""Memory store access shared by context retrieval."""

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from smriti.config import Config, load_config
from smriti.memory import MemoryStore
from smriti.server.snapshots import IndexStore


@contextmanager
def memory_store(
    root: Path, *, sync_git: bool = True, config: Config | None = None
) -> Iterator[MemoryStore]:
    config = config or load_config(root)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    store = MemoryStore(config.data_dir / 'memory.sqlite')
    try:
        result = subprocess.run(
            ['git', '-C', str(config.root), 'rev-parse', '--verify', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=10,
        )
        commit = result.stdout.strip() if result.returncode == 0 else None
        if sync_git and commit:
            store.sync_git(config.root)
        index = config.data_dir / 'index.sqlite'
        if index.exists():
            snapshot = IndexStore(index).load()
            store.refresh(
                {symbol.id: symbol.content_hash for symbol in snapshot.symbols}, commit=commit
            )
        yield store
    finally:
        store.close()
