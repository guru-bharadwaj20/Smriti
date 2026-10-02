import sqlite3
from pathlib import Path

import pytest

from smriti.models import Symbol
from smriti.server.snapshots import IndexStore


def test_error_mid_update_rolls_back_every_table(tmp_path: Path) -> None:
    store = IndexStore(tmp_path / 'index.sqlite')
    first = Symbol('first', 'first.py', 'f', 'f', 'function')
    store.publish([first], [], {'first.py': 'one'}, expected_version=0)
    before = store.load()
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "CREATE TRIGGER stop_write BEFORE INSERT ON symbols BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
        )
    second = Symbol('second', 'second.py', 'g', 'g', 'function')
    with pytest.raises(sqlite3.IntegrityError):
        store.publish([second], [], {'second.py': 'two'}, expected_version=1)
    assert store.load() == before
