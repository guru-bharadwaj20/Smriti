"""Guard repository identity and clean base state before benchmark retrieval."""

import subprocess
from pathlib import Path


def validate_checkout(checkout: Path, expected_commit: str, expected_source: str) -> None:
    def git(*arguments: str) -> str:
        return subprocess.check_output(['git', '-C', str(checkout), *arguments], text=True).strip()

    actual_commit = git('rev-parse', 'HEAD')
    if actual_commit.lower() != expected_commit.lower():
        raise ValueError('Checkout is not at the benchmark base commit')
    actual_source = git('remote', 'get-url', 'origin')
    if actual_source.removesuffix('.git').rstrip('/') != expected_source.removesuffix(
        '.git'
    ).rstrip('/'):
        raise ValueError('Checkout origin does not match benchmark repository')
    if git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Benchmark checkout must be clean before indexing')
