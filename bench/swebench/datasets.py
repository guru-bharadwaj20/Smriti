"""Immutable public SWE-bench artifact downloads with checksum/row validation."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.swebench.splits import SPLIT_POLICY, instance_split

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ROWS = {'princeton-nlp/SWE-bench_Lite': 300, 'princeton-nlp/SWE-bench_Verified': 500}


@dataclass(frozen=True)
class Task:
    dataset: str
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    patch: str

    @property
    def evaluation_id(self) -> str:
        identity = '\0'.join([self.repo, self.base_commit, self.problem_statement, self.patch])
        digest = hashlib.sha256(identity.encode()).hexdigest()[:16]
        return self.instance_id + '-' + digest


def download_datasets(data_root: Path = ROOT / 'bench' / 'data') -> dict[str, Any]:
    pins = json.loads((ROOT / 'bench' / 'datasets.json').read_text(encoding='utf-8'))
    manifest: dict[str, Any] = {}
    for dataset, count in EXPECTED_ROWS.items():
        revision = pins[dataset]['revision']
        metadata_url = f'https://huggingface.co/api/datasets/{dataset}/tree/{revision}/data'
        with urllib.request.urlopen(metadata_url, timeout=60) as response:
            entries = json.load(response)
        files = [
            entry
            for entry in entries
            if entry['type'] == 'file'
            and Path(entry['path']).name.startswith('test-')
            and entry['path'].endswith('.parquet')
        ]
        if not files:
            raise ValueError(f'No pinned test parquet artifacts for {dataset}')
        artifacts = []
        for entry in files:
            destination = (
                data_root / dataset.rsplit('/', 1)[-1] / revision / Path(entry['path']).name
            ).resolve()
            if not destination.is_relative_to(data_root.resolve()):
                raise ValueError('Dataset path escaped benchmark data directory')
            destination.parent.mkdir(parents=True, exist_ok=True)
            url = f'https://huggingface.co/datasets/{dataset}/resolve/{revision}/{entry["path"]}'
            expected = entry.get('lfs', {}).get('oid')
            if not destination.exists():
                temporary = destination.with_suffix('.partial')
                with (
                    urllib.request.urlopen(url, timeout=120) as response,
                    temporary.open('wb') as output,
                ):
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                temporary.replace(destination)
            with destination.open('rb') as file:
                actual = hashlib.file_digest(file, 'sha256').hexdigest()
            if expected is not None and actual != expected:
                raise ValueError(f'Official checksum mismatch: {dataset}/{entry["path"]}')
            import pyarrow.parquet as parquet

            rows = parquet.ParquetFile(destination).metadata.num_rows
            artifacts.append(
                {
                    'path': destination.relative_to(ROOT).as_posix(),
                    'source': url,
                    'sha256': actual,
                    'publisher_sha256': expected,
                    'bytes': destination.stat().st_size,
                    'rows': rows,
                }
            )
        if sum(file['rows'] for file in artifacts) != count:
            raise ValueError(f'Unexpected pinned test row count for {dataset}')
        manifest[dataset] = {
            'revision': revision,
            'split': 'test',
            'rows': count,
            'artifacts': artifacts,
        }
    return manifest


def load_tasks(manifest: dict[str, Any]) -> list[Task]:
    import pyarrow.parquet as parquet

    result = []
    for dataset, info in manifest.items():
        for artifact in info['artifacts']:
            for row in parquet.read_table(ROOT / artifact['path']).to_pylist():
                result.append(
                    Task(
                        dataset,
                        row['instance_id'],
                        row['repo'],
                        row['base_commit'],
                        row['problem_statement'],
                        row['patch'],
                    )
                )
    return sorted(
        result, key=lambda task: (task.repo, task.base_commit, task.instance_id, task.dataset)
    )


def run_manifest(tasks: list[Task], artifacts: dict[str, Any]) -> dict[str, Any]:
    return {
        'artifacts': artifacts,
        'split_policy': SPLIT_POLICY,
        'dataset_rows': len(tasks),
        'unique_evaluations': len({task.evaluation_id for task in tasks}),
        'note': 'Overlapping dataset rows reuse results only when repository, base commit, exact query and gold patch all agree. No issue/patch payload is redistributed here.',
        'instances': [
            {
                'dataset': task.dataset,
                'instance_id': task.instance_id,
                'evaluation_id': task.evaluation_id,
                'repo': task.repo,
                'base_commit': task.base_commit,
                'split': instance_split(task.instance_id),
            }
            for task in tasks
        ],
    }


if __name__ == '__main__':
    artifacts = download_datasets()
    path = ROOT / 'bench' / 'swebench' / 'dataset_artifacts.json'
    path.write_text(json.dumps(artifacts, indent=2) + '\n', encoding='utf-8')
    tasks = load_tasks(artifacts)
    (path.parent / 'run_manifest.json').write_text(
        json.dumps(run_manifest(tasks, artifacts), indent=2) + '\n', encoding='utf-8'
    )
    print(
        json.dumps(
            {
                'rows': len(tasks),
                'unique_evaluations': len({task.evaluation_id for task in tasks}),
                'repositories': sorted({task.repo for task in tasks}),
            },
            indent=2,
        )
    )
