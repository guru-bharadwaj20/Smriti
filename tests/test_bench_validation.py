import subprocess
from pathlib import Path

import pytest

from bench.swebench.validation import validate_checkout


def test_wrong_commit_repository_and_modified_worktree_are_rejected(tmp_path: Path) -> None:
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        [
            'git',
            '-C',
            str(tmp_path),
            'remote',
            'add',
            'origin',
            'https://github.com/example/project.git',
        ],
        check=True,
    )
    subprocess.run(
        [
            'git',
            '-C',
            str(tmp_path),
            '-c',
            'user.name=fixture',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '--allow-empty',
            '-m',
            'base',
        ],
        check=True,
        capture_output=True,
    )
    commit = subprocess.check_output(
        ['git', '-C', str(tmp_path), 'rev-parse', 'HEAD'], text=True
    ).strip()
    validate_checkout(tmp_path, commit, 'https://github.com/example/project')
    with pytest.raises(ValueError, match='base commit'):
        validate_checkout(tmp_path, '0' * 40, 'https://github.com/example/project')
    with pytest.raises(ValueError, match='repository'):
        validate_checkout(tmp_path, commit, 'https://github.com/example/other')
    (tmp_path / 'unexpected.py').write_text('patch = True\n', encoding='utf-8')
    with pytest.raises(ValueError, match='clean'):
        validate_checkout(tmp_path, commit, 'https://github.com/example/project')
