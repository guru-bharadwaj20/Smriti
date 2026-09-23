from typer.testing import CliRunner

from smriti.server.cli import app


def test_version_entry_point() -> None:
    result = CliRunner().invoke(app, ['version'])
    assert result.exit_code == 0
    assert result.stdout.strip() == '0.1.0'
