from pathlib import Path

from smriti.server.service import SmritiService


def test_symbol_lookup_and_resolved_graph_persist_together(tmp_path: Path) -> None:
    (tmp_path / 'app.py').write_text(
        'def target():\n    return 1\n\ndef caller():\n    return target()\n', encoding='utf-8'
    )
    service = SmritiService(tmp_path)
    service.index()
    (target,) = service.find_symbol('target')
    (caller,) = service.find_symbol('caller')
    assert service.find_symbol(target.id) == [target]
    assert any(
        edge.source == caller.id and edge.target == target.id and edge.kind == 'calls'
        for edge in service.snapshot().edges
    )
    assert SmritiService(tmp_path).find_symbol('target') == [target]
