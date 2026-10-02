"""Optional coding-agent task-success comparison: issue only vs. issue + Smriti context.

A local model acts as a single-shot agent. For every task it receives the issue
and either (a) the repository file list or (b) Smriti's packed context at a fixed
token budget, and must answer with one corrected Python function. The function
replaces the same-named definition in a fresh copy of the fixture, and the task's
check runs in a subprocess. Success is that check passing. Nothing else differs
between conditions.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from smriti.config import Config
from smriti.parse import SourceParser
from smriti.server.service import SmritiService

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / 'fixture'
INSTRUCTION = (
    'You are fixing a bug in a Python project. Reply with exactly one corrected '
    'Python function definition inside a ```python code block and nothing else. '
    'Keep the function name and parameters unchanged.'
)


def prompt(issue: str, condition: str, workdir: Path, budget: int) -> str:
    if condition == 'baseline':
        files = sorted(p.relative_to(workdir).as_posix() for p in workdir.rglob('*.py'))
        material = 'Repository files:\n' + '\n'.join(files)
    else:
        service = SmritiService(workdir, Config(workdir, workdir.parent / 'state'))
        material = 'Relevant code:\n' + service.context(issue, budget).text
    return f'{INSTRUCTION}\n\nIssue: {issue}\n\n{material}\n'


def extract_function(reply: str) -> tuple[str, str] | None:
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', reply, re.DOTALL) or [reply]
    for block in blocks:
        match = re.search(r'^def\s+(\w+)\s*\(', block, re.MULTILINE)
        if match:
            return match.group(1), block[match.start() :].rstrip() + '\n'
    return None


def apply(workdir: Path, name: str, code: str) -> str | None:
    """Replace the unique top-level function `name`; return its path or None."""
    parser = SourceParser()
    hits = []
    for path in sorted(workdir.rglob('*.py')):
        relative = path.relative_to(workdir).as_posix()
        for symbol in parser.parse(relative, path.read_bytes()).symbols:
            if symbol.kind == 'function' and symbol.name == name:
                hits.append((path, symbol))
    if len(hits) != 1:
        return None
    path, symbol = hits[0]
    source = path.read_bytes()
    path.write_bytes(source[: symbol.start_byte] + code.encode() + source[symbol.end_byte :])
    return path.relative_to(workdir).as_posix()


def check(workdir: Path, code: str) -> bool:
    result = subprocess.run(
        # -B: a .pyc from the buggy run can look current when the fix lands in the same
        # second (mtime has 1 s resolution), which silently re-runs the buggy code.
        [sys.executable, '-B', '-c', code],
        cwd=workdir,
        capture_output=True,
        timeout=60,
    )
    return result.returncode == 0


def inject(workdir: Path, task: dict[str, object]) -> None:
    """Introduce exactly this task's bug; the clean fixture must pass its check first."""
    spec = task['inject']
    assert isinstance(spec, dict)
    if not check(workdir, str(task['check'])):
        raise AssertionError(f'Task {task["id"]} fails on the clean fixture')
    path = workdir / spec['path']
    source = path.read_text(encoding='utf-8')
    if source.count(spec['correct']) != 1:
        raise AssertionError(f'Task {task["id"]} injection site is not unique')
    path.write_text(source.replace(spec['correct'], spec['bug']), encoding='utf-8')
    if check(workdir, str(task['check'])):
        raise AssertionError(f'Task {task["id"]} still passes after injecting its bug')


def run(generate: Callable[[str], str], model: str, budget: int = 1500) -> dict[str, object]:
    tasks = json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))
    rows = []
    for task in tasks:
        for condition in ('baseline', 'smriti'):
            # SQLite handles can outlive the service on Windows; never fail on cleanup.
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
                workdir = Path(directory) / 'repo'
                shutil.copytree(FIXTURE, workdir, ignore=shutil.ignore_patterns('__pycache__'))
                inject(workdir, task)
                text = prompt(task['issue'], condition, workdir, budget)
                started = time.perf_counter()
                reply = generate(text)
                seconds = time.perf_counter() - started
                found = extract_function(reply)
                edited = apply(workdir, *found) if found else None
                rows.append(
                    {
                        'task': task['id'],
                        'condition': condition,
                        'function': found[0] if found else None,
                        'edited_path': edited,
                        'success': bool(edited) and check(workdir, task['check']),
                        'prompt_chars': len(text),
                        'generation_seconds': seconds,
                    }
                )
                print(json.dumps(rows[-1]), flush=True)
    summary = {
        condition: {
            'tasks': len(tasks),
            'solved': sum(r['success'] for r in rows if r['condition'] == condition),
            'edited_some_function': sum(
                r['edited_path'] is not None for r in rows if r['condition'] == condition
            ),
        }
        for condition in ('baseline', 'smriti')
    }
    return {
        'schema_version': 1,
        'model': model,
        'decoding': 'temperature 0, seed 0, single attempt per task and condition',
        'context_budget_tokens': budget,
        'summary': summary,
        'rows': rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path, help='local GGUF instruct model')
    parser.add_argument('--budget', type=int, default=1500)
    parser.add_argument('--output', type=Path, default=HERE / 'results.json')
    args = parser.parse_args()
    from smriti.memory.summaries import LlamaCppGenerator

    generator = LlamaCppGenerator(args.model, max_tokens=400)
    result = run(generator, generator.model, args.budget)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
