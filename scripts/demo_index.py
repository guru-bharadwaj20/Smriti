"""Run cold indexing and a single-line edit in an isolated temporary repository."""

import argparse
import json
import platform
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from smriti.server.service import SmritiService


def run(files: int = 100) -> dict[str, object]:
    if files < 1:
        raise ValueError('files must be positive')
    with TemporaryDirectory(prefix='smriti-index-demo-') as directory:
        root = Path(directory)
        for number in range(files):
            (root / f'worker_{number}.py').write_text(
                f'def work_{number}():\n    return {number}\n', encoding='utf-8'
            )
        service = SmritiService(root)
        started = perf_counter()
        cold = service.index()
        cold_seconds = perf_counter() - started
        (root / 'worker_0.py').write_text('def work_0():\n    return -1\n', encoding='utf-8')
        started = perf_counter()
        edited = service.index()
        edited_seconds = perf_counter() - started
        assert cold.files == files and cold.changed_files == files
        assert edited.changed_files == 1
        assert next(
            symbol for symbol in service.snapshot().symbols if symbol.name == 'work_0'
        ).body.endswith('return -1')
        return {
            'scenario': 'cold index followed by one-line edit',
            'python': platform.python_version(),
            'platform': platform.platform(),
            'files': files,
            'cold_seconds': cold_seconds,
            'edit_seconds': edited_seconds,
            'cold': asdict(cold),
            'edited': asdict(edited),
            'scope': 'Single synthetic repository run; not a production latency benchmark.',
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--files', type=int, default=100)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = json.dumps(run(args.files), indent=2)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
