"""Reproducible selection of real first-parent repository histories."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def sequence_digest(commits: list[dict[str, Any]]) -> str:
    return hashlib.sha256('\n'.join(row['sha'] for row in commits).encode('ascii')).hexdigest()


def validate_manifest(document: dict[str, Any], expected_count: int | None = None) -> None:
    commits = document['commits']
    count = expected_count if expected_count is not None else document['requested_count']
    if count < 1 or len(commits) != count or document['actual_count'] != count:
        raise ValueError('The manifest does not contain the requested number of real commits')
    if len({row['sha'] for row in commits}) != count:
        raise ValueError('Replay commits must be unique')
    if document['sequence_sha256'] != sequence_digest(commits):
        raise ValueError('Replay sequence checksum mismatch')
    for previous, current in zip(commits, commits[1:], strict=False):
        if not current['parents'] or current['parents'][0] != previous['sha']:
            raise ValueError('Replay must follow actual first-parent ancestry')
    if commits[-1]['sha'] != document['tip']:
        raise ValueError('Replay tip differs from the recorded repository revision')


def generate_manifest(checkout: Path, count: int = 200, tip: str = 'HEAD') -> dict[str, Any]:
    if count < 1:
        raise ValueError('count must be positive')
    result = subprocess.run(
        [
            'git',
            '-C',
            str(checkout),
            'log',
            '--first-parent',
            '-n',
            str(count),
            '--format=%H%x00%P%x00%cI%x00%aI',
            tip,
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    commits: list[dict[str, Any]] = []
    for line in reversed(result.stdout.splitlines()):
        sha, parents, committed_at, authored_at = line.split(chr(0))
        commits.append(
            {
                'sha': sha,
                'parents': parents.split(),
                'committed_at': committed_at,
                'authored_at': authored_at,
            }
        )
    origin = subprocess.run(
        ['git', '-C', str(checkout), 'remote', 'get-url', 'origin'],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    document = {
        'schema_version': 1,
        'repository': origin,
        'tip': commits[-1]['sha'] if commits else '',
        'requested_count': count,
        'actual_count': len(commits),
        'ordering': 'first-parent ancestry; timestamps do not determine ordering',
        'sequence_sha256': sequence_digest(commits),
        'commits': commits,
    }
    validate_manifest(document, count)
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.smriti/replay/requests'))
    parser.add_argument('--count', type=int, default=200)
    parser.add_argument('--tip', default='HEAD')
    parser.add_argument('--output', type=Path, default=Path('bench/codemem/requests-200.json'))
    args = parser.parse_args()
    document = generate_manifest(args.repo, args.count, args.tip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print(
        json.dumps(
            {
                'count': document['actual_count'],
                'tip': document['tip'],
                'sequence_sha256': document['sequence_sha256'],
            }
        )
    )


if __name__ == '__main__':
    main()
