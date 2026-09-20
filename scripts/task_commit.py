"""Serialize task commits and immediate pushes across parallel contributors."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / '.task-commit-lock'


def git(*args: str) -> str:
    result = subprocess.run(
        ['git', '-c', 'user.name=guru-bharadwaj20',
         '-c', 'user.email=gururb20@gmail.com', *args],
        cwd=ROOT, text=True, capture_output=True,
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
    deadline = time.monotonic() + 300
    while True:
        try:
            LOCK.mkdir()
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise RuntimeError('Commit lock timed out; inspect owner before removal')
            time.sleep(0.25)
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
        text = checklist.read_text(encoding='utf-8')
        pattern = re.compile(r'^\| ❌ Pending \| ' + re.escape(args.task) + r' \| ([^|]+) \| [^|]*\|$', re.MULTILINE)
        if len(pattern.findall(text)) != 1:
            raise ValueError(f'Expected one pending checklist row for {args.task}')
        evidence = args.evidence.replace('|', '/')
        text = pattern.sub(lambda match: f'| ✅ Done | {args.task} | {match.group(1).strip()} | {evidence} |', text)
        checklist.write_text(text, encoding='utf-8', newline='\n')
        git('add', '--', *paths, 'CONTRIBUTING.md')
        git('diff', '--cached', '--check')
        print(git('commit', '-m', f'{args.task}: {args.message}'), flush=True)
        # A failed push stops this worker; never silently accumulate local commits.
        print(git('push'), flush=True)
    finally:
        (LOCK / 'owner').unlink(missing_ok=True)
        LOCK.rmdir()


if __name__ == '__main__':
    main()
