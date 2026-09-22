from pathlib import Path

import pytest

from smriti.models import Symbol
from smriti.server.snapshots import ConcurrentUpdateError, IndexStore


def test_retained_snapshot_is_immutable_and_versions_are_consistent(tmp_path: Path) -> None:
    store = IndexStore(tmp_path / 'index.sqlite')
    original = store.load()
    symbol = Symbol('one', 'a.py', 'f', 'f', 'function')
    assert store.publish([symbol], [], {'a.py': 'hash'}, expected_version=0) == 1
    current = store.load()
    assert original.version == 0 and original.symbols == ()
    assert current.symbols == (symbol,) and current.files['a.py'] == 'hash'
    with pytest.raises(TypeError):
        current.files['a.py'] = 'other'  # type: ignore[index]
    with pytest.raises(ConcurrentUpdateError):
        store.publish([], [], {}, expected_version=0)
    assert store.load() == current
