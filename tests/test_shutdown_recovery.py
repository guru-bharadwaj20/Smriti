import os
import subprocess
import sys
from pathlib import Path

import pytest

from smriti.server.jobs import BackgroundIndexer, IndexingError
from smriti.server.service import MemoryService, SmritiService


def test_close_is_idempotent_and_rejects_new_jobs(tmp_path: Path) -> None:
    (tmp_path / 'a.py').write_text('def a():\n    pass\n')
    with BackgroundIndexer() as worker:
        assert worker.submit(tmp_path).result(timeout=60).files == 1
    worker.close()
    with pytest.raises(IndexingError):
        worker.submit(tmp_path)


def test_restart_after_killed_process_recovers_committed_state(tmp_path: Path) -> None:
    (tmp_path / 'a.py').write_text('def a():\n    pass\n')
    code = (
        'import os, sys\n'
        'from pathlib import Path\n'
        'from smriti.server.service import MemoryService, SmritiService\n'
        'root = Path(sys.argv[1])\n'
        'SmritiService(root).index()\n'
        "MemoryService(root).remember('Survives a crash')\n"
        'os._exit(13)\n'
    )
    result = subprocess.run(
        [sys.executable, '-c', code, str(tmp_path)],
        timeout=120,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ},
    )
    assert result.returncode == 13
    assert SmritiService(tmp_path).snapshot().version == 1
    memory = MemoryService(tmp_path)
    try:
        assert [fact['text'] for fact in memory.recall()] == ['Survives a crash']
        assert memory.store.verify()
    finally:
        memory.close()
