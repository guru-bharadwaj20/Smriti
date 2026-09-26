import json
from pathlib import Path

from typer.testing import CliRunner

from smriti.server.cli import app
from smriti.server.service import SmritiService


def test_callers_callees_use_persisted_resolved_graph(tmp_path: Path) -> None:
    (tmp_path / 'sample.py').write_text(
        'def normalize(value):\n    return value\n\ndef caller():\n    return normalize(1)\n'
    )
    service = SmritiService(tmp_path)
    service.index()
    normalize = service.find_symbol('normalize')[0]
    caller = service.find_symbol('caller')[0]
    runner = CliRunner()
    for command, name in [('callers', 'normalize'), ('callees', 'caller')]:
        result = runner.invoke(app, [command, name, '--root', str(tmp_path)])
        assert result.exit_code == 0, result.output
        edges = json.loads(result.output)
        assert any(edge['source'] == caller.id and edge['target'] == normalize.id for edge in edges)
