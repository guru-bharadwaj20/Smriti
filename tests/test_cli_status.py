import json
from pathlib import Path

from typer.testing import CliRunner

from smriti.server.cli import app


def test_status_does_not_create_unindexed_state(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ['status', '--root', str(tmp_path)])
    assert result.exit_code == 0
    assert json.loads(result.stdout)['indexed'] is False
    assert not (tmp_path / '.smriti').exists()
    (tmp_path / 'app.py').write_text('class App:\n    pass\n', encoding='utf-8')
    assert runner.invoke(app, ['index', '--root', str(tmp_path)]).exit_code == 0
    data = json.loads(runner.invoke(app, ['status', '--root', str(tmp_path)]).stdout)
    assert data['indexed'] is True and data['symbols'] == 2 and data['version'] == 1
