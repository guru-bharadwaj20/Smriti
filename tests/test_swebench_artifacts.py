import hashlib

import pytest

from bench.swebench.datasets import ROOT, Task, run_manifest
from bench.swebench.runner import verify_artifacts


def test_overlap_reuse_requires_exact_query_and_gold():
    first = Task(
        'lite',
        'same',
        'psf/requests',
        'a' * 40,
        'private issue payload sentinel',
        'private patch payload sentinel',
    )
    same = Task(
        'verified',
        'same',
        'psf/requests',
        'a' * 40,
        'private issue payload sentinel',
        'private patch payload sentinel',
    )
    changed = Task('verified', 'same', 'psf/requests', 'a' * 40, 'query', 'other')
    manifest = run_manifest([first, same, changed], {})
    assert manifest['dataset_rows'] == 3
    assert manifest['unique_evaluations'] == 2
    assert len({row['split'] for row in manifest['instances']}) == 1
    assert 'private issue payload sentinel' not in str(manifest)
    assert 'private patch payload sentinel' not in str(manifest)


def test_artifact_tamper_and_path_escape(tmp_path):
    path = ROOT / 'bench/data/checksum-test.tmp'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_bytes(b'original')
        manifest = {
            'test': {
                'artifacts': [
                    {
                        'path': path.relative_to(ROOT).as_posix(),
                        'sha256': hashlib.sha256(b'original').hexdigest(),
                    }
                ]
            }
        }
        verify_artifacts(manifest)
        path.write_bytes(b'changed')
        with pytest.raises(ValueError, match='Changed dataset'):
            verify_artifacts(manifest)
        manifest['test']['artifacts'][0]['path'] = 'pyproject.toml'
        with pytest.raises(ValueError, match='escaped'):
            verify_artifacts(manifest)
    finally:
        path.unlink(missing_ok=True)
