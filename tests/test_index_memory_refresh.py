import json
from pathlib import Path

from typer.testing import CliRunner

from smriti.server.cli import app

SOURCE = 'def parse_header(line):\n    return line.split(":", 1)\n'


def run(*args: str) -> object:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_cli_index_marks_edited_anchor_stale_and_follows_moves(tmp_path: Path) -> None:
    root = str(tmp_path)
    (tmp_path / 'app.py').write_text(SOURCE)
    run('index', '--root', root)
    symbol = run('find-symbol', 'parse_header', '--root', root)[0]
    anchor = f'{symbol["id"]}={symbol["content_hash"]}'
    fact = run('remember', 'keeps casing', '--anchor', anchor, '--root', root)
    (tmp_path / 'lib').mkdir()
    (tmp_path / 'app.py').rename(tmp_path / 'lib' / 'app.py')
    run('index', '--root', root)
    moved = run('recall', 'casing', '--root', root)[0]
    assert moved['id'] == fact['id'] and moved['freshness'] == 'fresh'
    assert moved['anchors'][0]['symbol_id'] != symbol['id']
    (tmp_path / 'lib' / 'app.py').write_text(SOURCE.replace('line.split', 'line.lower().split'))
    run('index', '--root', root)
    assert run('recall', 'casing', '--root', root)[0]['freshness'] == 'stale'
    assert run('recall', 'casing', '--fresh-only', '--root', root) == []
