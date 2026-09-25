from pathlib import Path

from smriti.server.service import SmritiService


def test_index_persists_and_updates_only_changed_files(tmp_path: Path) -> None:
    path = tmp_path / 'app.py'
    path.write_text('class Processor:\n    pass\n', encoding='utf-8')
    service = SmritiService(tmp_path)
    first = service.index()
    assert first.files == 1
    assert {symbol.name for symbol in service.snapshot().symbols} == {'app', 'Processor'}
    assert service.index().version == first.version
    assert SmritiService(tmp_path).snapshot() == service.snapshot()
    path.write_text('class Changed:\n    pass\n', encoding='utf-8')
    assert service.index().changed_files == 1
    assert {symbol.name for symbol in service.snapshot().symbols} == {'app', 'Changed'}
    path.unlink()
    assert service.index().symbols == 0
