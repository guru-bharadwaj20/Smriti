"""Serialize task commits and immediate pushes across parallel contributors."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / '.task-commit-lock'
QUEUE = ROOT / '.task-commit-queue'


def acquire_lock() -> Path:
    """FIFO tickets prevent fast workers from starving waiting contributors."""
    QUEUE.mkdir(exist_ok=True)
    ticket = QUEUE / f'{time.time_ns():020d}-{os.getpid()}-{uuid.uuid4().hex}'
    ticket.write_text(str(os.getpid()), encoding='utf-8')
    deadline = time.monotonic() + 1800
    try:
        while True:
            if min(QUEUE.iterdir(), key=lambda path: path.name) == ticket:
                try:
                    LOCK.mkdir()
                    return ticket
                except FileExistsError:
                    pass
            if time.monotonic() > deadline:
                raise RuntimeError('Commit lock timed out; inspect owner before removal')
            time.sleep(0.25)
    except BaseException:
        ticket.unlink(missing_ok=True)
        raise


def git(*args: str) -> str:
    result = subprocess.run(
        ['git', '-c', 'user.name=guru-bharadwaj20',
         '-c', 'user.email=gururb20@gmail.com', *args],
        cwd=ROOT, text=True, capture_output=True, timeout=120,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task')
    parser.add_argument('message')
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--files', nargs='+', required=True)
    args = parser.parse_args()
    ticket = acquire_lock()
    try:
        (LOCK / 'owner').write_text(str(os.getpid()), encoding='utf-8')
        if git('diff', '--cached', '--name-only'):
            raise RuntimeError('Index has staged changes; refusing to mix contributor work')
        paths = []
        for name in args.files:
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT) or '.git' in path.relative_to(ROOT).parts:
                raise ValueError('Only project files may be staged')
            paths.append(path.relative_to(ROOT).as_posix())
        checklist = ROOT / 'CONTRIBUTING.md'
        original_text = checklist.read_text(encoding='utf-8')
        text = original_text
        pattern = re.compile(r'^\| ❌ Pending \| ' + re.escape(args.task) + r' \| ([^|]+) \| [^|]*\|$', re.MULTILINE)
        if len(pattern.findall(text)) != 1:
            raise ValueError(f'Expected one pending checklist row for {args.task}')
        evidence = args.evidence.replace('|', '/')
        text = pattern.sub(lambda match: f'| ✅ Done | {args.task} | {match.group(1).strip()} | {evidence} |', text)
        checklist.write_text(text, encoding='utf-8', newline='\n')
        try:
            git('add', '--', *paths, 'CONTRIBUTING.md')
            git('diff', '--cached', '--check')
            print(git('commit', '-m', f'{args.task}: {args.message}'), flush=True)
        except Exception:
            # The index was empty on entry. Restore only this task's own staging
            # and checklist edit so other contributors can keep making progress.
            git('reset', '--', *paths, 'CONTRIBUTING.md')
            checklist.write_text(original_text, encoding='utf-8', newline='\n')
            raise
        # A failed push stops this worker; never silently accumulate local commits.
        print(git('push'), flush=True)
    finally:
        (LOCK / 'owner').unlink(missing_ok=True)
        LOCK.rmdir()
        ticket.unlink(missing_ok=True)
        # Give already-waiting workers a chance before this worker starts again.
        time.sleep(1)


if __name__ == '__main__':
    main()
