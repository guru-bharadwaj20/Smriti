"""Measure lossless archive compression on an actual replay memory database."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from smriti.memory import MemoryStore
from smriti.memory.sync import (
    compress_bundle,
    compression_metrics,
    decompress_bundle,
    export_bundle,
    verify_bundle,
)


def evaluate(database: Path, repository: str) -> dict[str, object]:
    if not database.is_file():
        raise ValueError('Compression evaluation requires an existing replay database')
    store = MemoryStore(database)
    try:
        key = os.urandom(32)
        bundle = export_bundle(store, repository, key)
        restored = decompress_bundle(compress_bundle(bundle))
        document = verify_bundle(restored, repository, key)
        return {
            'schema_version': 1,
            'repository': repository,
            'method': 'Lossless zlib level 9 over canonical authenticated operation/payload archive',
            **compression_metrics(bundle),
            'authenticated_after_decompression': document == bundle['document'],
            'operation_count': len(document['operations']),
            'payload_count': len(document['blobs']),
            'purged_identity_count': len(document['purged_ids']),
            'operation_log_verifies': store.verify(),
            'semantic_summary_generated': False,
        }
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--database', type=Path, default=Path('.smriti/replay/requests/.smriti/codemem.sqlite')
    )
    parser.add_argument('--repository', default='https://github.com/psf/requests.git')
    parser.add_argument(
        '--output', type=Path, default=Path('bench/codemem/results/compression.json')
    )
    args = parser.parse_args()
    document = evaluate(args.database, args.repository)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(document, indent=2))


if __name__ == '__main__':
    main()
