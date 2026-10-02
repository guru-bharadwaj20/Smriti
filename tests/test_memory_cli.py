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


def test_forget_cascades_by_fact_and_source(tmp_path: Path) -> None:
    first = invoke(tmp_path, 'remember', 'From the log', '--source', 'log', '--session', 's1')
    other = invoke(tmp_path, 'remember', 'Kept fact')
    assert isinstance(first, dict) and isinstance(other, dict)
    assert invoke(tmp_path, 'forget', '--source', 'log') == {'forgotten': [first['id']]}
    assert invoke(tmp_path, 'forget', other['id']) == {'forgotten': [other['id']]}
    assert invoke(tmp_path, 'recall') == []
    both = runner.invoke(app, ['forget', 'x', '--source', 'y', '--root', str(tmp_path)])
    assert both.exit_code != 0


def test_memory_log_and_diff(tmp_path: Path) -> None:
    fact = invoke(tmp_path, 'remember', 'First')
    assert isinstance(fact, dict)
    log = invoke(tmp_path, 'memory', 'log')
    assert isinstance(log, list) and log[0]['kind'] == 'add'
    assert invoke(tmp_path, 'memory', 'log', '--limit', '1') == log[:1]
    diff = invoke(tmp_path, 'memory', 'diff')
    assert isinstance(diff, dict) and list(diff['added']) == [fact['id']]
    assert invoke(tmp_path, 'memory', 'diff', log[0]['id']) == {
        'added': {},
        'removed': {},
        'changed': {},
    }


def test_memory_revert(tmp_path: Path) -> None:
    invoke(tmp_path, 'remember', 'Temporary')
    log = invoke(tmp_path, 'memory', 'log')
    assert isinstance(log, list)
    reverted = invoke(tmp_path, 'memory', 'revert', log[0]['id'])
    assert isinstance(reverted, dict) and reverted['operation']
    assert invoke(tmp_path, 'recall') == []
    again = runner.invoke(app, ['memory', 'revert', log[0]['id'], '--root', str(tmp_path)])
    assert again.exit_code != 0
