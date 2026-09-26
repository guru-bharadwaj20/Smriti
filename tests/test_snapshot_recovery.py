from pathlib import Path
import subprocess
import sys
from smriti.models import Symbol
from smriti.server.snapshots import IndexStore


def test_abrupt_writer_exit_does_not_publish_partial_index(tmp_path: Path) -> None:
    store = IndexStore(tmp_path / 'index.sqlite')
    first = Symbol('first', 'first.py', 'f', 'f', 'function')
    store.publish([first], [], {'first.py': 'one'}, expected_version=0)
    before = store.load()
    code = "import sqlite3,sys,os; c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN IMMEDIATE'); c.execute('DELETE FROM symbols'); c.execute('DELETE FROM files'); os._exit(17)"
    result = subprocess.run([sys.executable, '-c', code, str(store.path)], timeout=30)
    assert result.returncode == 17
    assert IndexStore(store.path).load() == before
