import json
from pathlib import Path

from typer.testing import CliRunner

from smriti.server.cli import app

runner = CliRunner()


def invoke(root: Path, *args: str, code: int = 0) -> object:
    result = runner.invoke(app, [*args, '--root', str(root)])
    assert result.exit_code == code, result.output
    return json.loads(result.output)


def test_remember_and_recall(tmp_path: Path) -> None:
    fact = invoke(tmp_path, 'remember', 'Parser caches grammars', '--source', 'doc')
    assert isinstance(fact, dict) and fact['source'] == 'doc'
    anchored = invoke(tmp_path, 'remember', 'Anchored', '--anchor', f'm.py:f={"a" * 64}')
    assert isinstance(anchored, dict) and anchored['scope'] == 'symbol'
    recalled = invoke(tmp_path, 'recall', 'grammars')
    assert isinstance(recalled, list) and recalled[0]['id'] == fact['id']
    bad = runner.invoke(app, ['remember', 'x', '--anchor', 'nohash', '--root', str(tmp_path)])
    assert bad.exit_code != 0
