import json
from pathlib import Path

from test_memory_mcp import run_tools
from typer.testing import CliRunner

from smriti.server.cli import app
from smriti.server.service import SmritiService


def cli(root: Path, *args: str) -> str:
    result = CliRunner().invoke(app, [*args, '--root', str(root)])
    assert result.exit_code == 0, result.output
    return result.output.rstrip('\n')


def test_cli_and_mcp_return_equivalent_results(tmp_path: Path) -> None:
    (tmp_path / 'm.py').write_text(
        'def parse_config(path):\n    return load(path)\n\n\ndef load(path):\n    return path\n'
    )
    SmritiService(tmp_path).index()
    cli(tmp_path, 'remember', 'Config parsing loads paths', '--source', 'notes')
    results = run_tools(
        tmp_path,
        [
            ('find_symbol', {'name': 'load'}),
            ('callers', {'name': 'load'}),
            ('callees', {'name': 'parse_config'}),
            ('context', {'task': 'parse config', 'budget': 300}),
            ('recall', {'query': 'config'}),
            ('memory_log', {}),
        ],
    )
    assert not any(result.is_error for result in results)
    structured = [result.structured_content for result in results]
    assert structured[0]['result'] == json.loads(cli(tmp_path, 'find-symbol', 'load'))
    assert structured[1]['result'] == json.loads(cli(tmp_path, 'callers', 'load'))
    assert structured[2]['result'] == json.loads(cli(tmp_path, 'callees', 'parse_config'))
    assert results[3].content[0].text.rstrip('\n') == cli(
        tmp_path, 'context', 'parse config', '--budget', '300'
    )
    assert structured[4]['result'] == json.loads(cli(tmp_path, 'recall', 'config'))
    assert structured[5]['result'] == json.loads(cli(tmp_path, 'memory', 'log'))
