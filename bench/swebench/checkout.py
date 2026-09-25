"""Isolated base-commit checkouts; patches are never applied here."""

import re
import subprocess
from pathlib import Path


def checkout_base(source: str, commit: str, destination: Path) -> Path:
    if not re.fullmatch(r'[0-9a-fA-F]{40}', commit):
        raise ValueError('Benchmark base commit must be a full Git SHA-1')
    if destination.exists():
        raise FileExistsError('Benchmark checkout must be a new isolated directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ['git', 'clone', '--no-checkout', '--', source, str(destination)],
        check=True,
        capture_output=True,
        timeout=300,
    )
    subprocess.run(
        ['git', '-C', str(destination), 'checkout', '--detach', commit],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return destination
