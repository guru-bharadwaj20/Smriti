"""Replay actual pinned commits through Smriti indexing and durable memory."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from smriti.memory import MemoryStore
from smriti.server.service import SmritiService

from .injection import fixture, inject, select_probes
from .labels import identical_renames, label
from .manifest import generate_manifest, validate_manifest
from .metrics import stale_metrics


def checkout(repo: Path, revision: str) -> None:
    subprocess.run(
        ['git', '-C', str(repo), 'checkout', '--quiet', '--detach', revision], check=True
    )


def replay(
    repo: Path, manifest: dict[str, Any], output: Path, limit: int = 64, cold_index: bool = False
) -> dict[str, object]:
    validate_manifest(manifest)
    if repo.resolve() == Path(__file__).resolve().parents[2]:
        raise ValueError('Replay requires an isolated source checkout, never the Smriti workspace')
    actual_manifest = generate_manifest(repo, len(manifest['commits']), manifest['tip'])
    if actual_manifest['commits'] != manifest['commits']:
        raise ValueError('Recorded commit metadata does not match actual source Git objects')
    if actual_manifest['repository'] != manifest['repository']:
        raise ValueError('The replay source remote differs from the recorded repository')
    if subprocess.run(
        ['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=no'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip():
        raise ValueError('Replay checkout has modified tracked source')
    output.mkdir(parents=True, exist_ok=True)
    database = repo / '.smriti' / 'codemem.sqlite'
    if database.exists():
        raise ValueError('Remove the isolated replay database before a new run')
    original = subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True
    ).stdout.strip()
    rows: list[dict[str, object]] = []
    rename_rows: list[dict[str, object]] = []
    store: MemoryStore | None = None
    try:
        first = manifest['commits'][0]['sha']
        checkout(repo, first)
        service = SmritiService(repo.resolve())
        service.index()
        previous = {
            s.id: s.content_hash for s in service.snapshot().symbols if s.path != '<external>'
        }
        probes = select_probes(service.snapshot().symbols, limit)
        (output / 'injection.json').write_text(
            json.dumps(fixture(probes, first), indent=2) + '\n', encoding='utf-8'
        )
        store = MemoryStore(database)
        store.sync_git(repo)
        inject(store, probes, first)
        oracle = {p.fact_id: (p.symbol_id, p.content_hash) for p in probes}
        for number, revision in enumerate(manifest['commits'][1:], 1):
            sha = revision['sha']
            checkout(repo, sha)
            if cold_index:
                service.parser.cache.clear()
            result = service.index()
            current = {
                s.id: s.content_hash for s in service.snapshot().symbols if s.path != '<external>'
            }
            renames = identical_renames(previous, current)
            store.sync_git(repo)
            expected = {
                identity: label(
                    symbol,
                    digest,
                    current,
                    {old: new for old, new in renames.items() if current[new] == digest},
                )
                for identity, (symbol, digest) in oracle.items()
            }
            store.refresh(current, renames=renames, commit=sha)
            observed = {f.id: f for f in store.recall()}
            for identity, target in expected.items():
                fact = observed[identity]
                rows.append(
                    {
                        'commit': sha,
                        'step': number,
                        'fact_id': identity,
                        **asdict(target),
                        'observed': fact.freshness,
                        'changed_files': result.changed_files,
                    }
                )
                old_symbol, _ = oracle[identity]
                if target.symbol_id != old_symbol:
                    rename_rows.append(
                        {
                            'commit': sha,
                            'fact_id': identity,
                            'old_symbol': old_symbol,
                            'new_symbol': target.symbol_id,
                            'survived': fact.anchors[0].symbol_id == target.symbol_id,
                        }
                    )
                oracle[identity] = (target.symbol_id, target.content_hash)
                if target.symbol_id in current:
                    digest = current[target.symbol_id]
                    if fact.freshness != 'fresh':
                        store.update(identity, text='Implementation fingerprint: ' + digest)
                        store.revalidate(identity, current, commit=sha)
                    oracle[identity] = (target.symbol_id, digest)
            previous = current
            if number % 25 == 0:
                print(
                    json.dumps({'replayed': number + 1, 'total': len(manifest['commits'])}),
                    flush=True,
                )
        source = probes[0].fact_id
        store.remember('Derived left', fact_id='cascade-left', derived_from=[source])
        store.remember('Derived right', fact_id='cascade-right', derived_from=[source])
        store.remember(
            'Derived diamond',
            fact_id='cascade-join',
            derived_from=['cascade-left', 'cascade-right'],
        )
        expected_removed = {source, 'cascade-left', 'cascade-right', 'cascade-join'}
        removed = set(store.forget(source))
        resurrected: list[str] = []
        for branch in store.branches():
            store.switch(branch)
            resurrected.extend(sorted({f.id for f in store.recall()} & expected_removed))
        cascade = {
            'expected_removed': sorted(expected_removed),
            'actual_removed': sorted(removed),
            'exact_closure': removed == expected_removed,
            'resurrected_ids': resurrected,
            'history_branches_checked': len(store.branches()),
            'operation_log_verifies': store.verify(),
        }
        metrics = {
            'schema_version': 1,
            'repository': manifest['repository'],
            'sequence_sha256': manifest['sequence_sha256'],
            'actual_commits': len(manifest['commits']),
            'parser_mode': 'fresh trees for changed files' if cold_index else 'incremental trees',
            'probes': len(probes),
            'policy': 'Assess implementation changes against previous validated fingerprint, then explicitly revalidate existing symbols. Missing anchors remain conservative.',
            'staleness': stale_metrics(rows),
            'rename_survival': {
                'eligible_events': len(rename_rows),
                'survived': sum(bool(r['survived']) for r in rename_rows),
                'rate': sum(bool(r['survived']) for r in rename_rows) / len(rename_rows)
                if rename_rows
                else None,
            },
            'cascade': cascade,
        }
        (output / 'labels.jsonl').write_text(
            ''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows), encoding='utf-8'
        )
        (output / 'renames.json').write_text(
            json.dumps(rename_rows, indent=2) + '\n', encoding='utf-8'
        )
        (output / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
        return metrics
    finally:
        if store is not None:
            store.close()
        checkout(repo, original)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.smriti/replay/requests'))
    parser.add_argument('--manifest', type=Path, default=Path('bench/codemem/requests-200.json'))
    parser.add_argument('--output', type=Path, default=Path('bench/codemem/results'))
    parser.add_argument('--probes', type=int, default=64)
    parser.add_argument(
        '--cold-index',
        action='store_true',
        help='Disable incremental tree reuse; record this mode in measurements',
    )
    args = parser.parse_args()
    print(
        json.dumps(
            replay(
                args.repo,
                json.loads(args.manifest.read_text(encoding='utf-8')),
                args.output,
                args.probes,
                args.cold_index,
            ),
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
