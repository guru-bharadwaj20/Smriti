from pathlib import Path

from smriti.server.jobs import BackgroundIndexer
from smriti.server.snapshots import IndexStore


def test_index_runs_in_worker_and_publishes_persisted_snapshot(tmp_path: Path) -> None:
    (tmp_path / 'app.py').write_text('class Processor:\n    pass\n', encoding='utf-8')
    worker = BackgroundIndexer()
    try:
        result = worker.submit(tmp_path).result(timeout=60)
        snapshot = IndexStore(tmp_path / '.smriti/index.sqlite').load()
        assert result.symbols == len(snapshot.symbols) == 2
        assert result.version == snapshot.version
    finally:
        worker.close()
