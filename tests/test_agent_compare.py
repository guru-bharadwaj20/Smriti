import json
import re
from pathlib import Path

from bench.agent.compare import FIXTURE, HERE, extract_function, run
from smriti.parse import SourceParser

TASKS = json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))


def oracle(prompt: str) -> str:
    """Return the clean fixture's version of the function this task breaks."""
    issue = re.search(r'Issue: (.*)', prompt).group(1)  # type: ignore[union-attr]
    task = next(t for t in TASKS if t['issue'] == issue)
    path = task['inject']['path']
    source = (FIXTURE / path).read_bytes()
    for symbol in SourceParser().parse(path, source).symbols:
        if symbol.kind == 'function' and task['inject']['correct'] in symbol.body:
            return f'```python\n{symbol.body}\n```'
    raise AssertionError(task['id'])


def test_oracle_solves_every_task_and_noop_solves_none() -> None:
    solved = run(oracle, 'oracle', budget=800)['summary']
    assert solved['baseline']['solved'] == solved['smriti']['solved'] == len(TASKS) == 8
    assert run(lambda prompt: 'no idea', 'noop', budget=800)['summary']['smriti']['solved'] == 0


def test_extract_function_handles_fenced_and_bare_replies() -> None:
    assert extract_function('```python\ndef f(x):\n    return x\n```')[0] == 'f'  # type: ignore[index]
    assert extract_function('Sure!\ndef g():\n    pass') == ('g', 'def g():\n    pass\n')
    assert extract_function('nothing') is None


def test_smriti_prompt_contains_the_buggy_function() -> None:
    from bench.agent.compare import prompt

    assert Path(FIXTURE / 'shop/money.py').exists()
    text = prompt(TASKS[0]['issue'], 'baseline', FIXTURE, 800)
    assert 'shop/money.py' in text and 'def to_cents' not in text


def test_smriti_prompt_contains_each_tasks_buggy_function(tmp_path: Path) -> None:
    import shutil

    from bench.agent.compare import inject, prompt

    for task in TASKS:
        workdir = tmp_path / task['id'] / 'repo'
        shutil.copytree(FIXTURE, workdir)
        inject(workdir, task)
        text = prompt(task['issue'], 'smriti', workdir, 1500)
        assert task['inject']['bug'] in text, task['id']
