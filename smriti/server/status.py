"""Read index status without creating state for an unindexed repository."""

from dataclasses import dataclass
from pathlib import Path

from smriti.config import load_config
from smriti.server.snapshots import IndexStore


@dataclass(frozen=True)
class IndexStatus:
    indexed: bool
    version: int
    files: int
    symbols: int
    edges: int


def index_status(root: Path) -> IndexStatus:
    config = load_config(root)
    database = config.data_dir / 'index.sqlite'
    if not database.exists():
        return IndexStatus(False, 0, 0, 0, 0)
    snapshot = IndexStore(database).load()
    return IndexStatus(
        bool(snapshot.version),
        snapshot.version,
        len(snapshot.files),
        len(snapshot.symbols),
        len(snapshot.edges),
    )
