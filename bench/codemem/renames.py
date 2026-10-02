"""Controlled rename survival on real Requests code in an isolated checkout.

The 200-commit history contains no unique matching-hash identity change touching a
probe, so replay alone leaves rename survival unmeasured. This experiment applies
real renames to the pinned tip: each probed module is moved to a new path with
identical bytes (an eligible verified rename), and each probed function separately
has its identifier changed (ineligible: the implementation hash changes). Every
mutation is reverted and the checkout is verified clean afterward.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from smriti.config import Config
from smriti.memory import MemoryStore
from smriti.server.service import SmritiService

from .injection import inject, select_probes
from .labels import identical_renames


def _clean(repo: Path) -> None:
    status = subprocess.run(
        ['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=all'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    dirty = [line for line in status.splitlines() if not line[3:].startswith('.smriti/')]
    if dirty:
        raise ValueError('Rename experiment requires a clean isolated checkout')


def _hashes(service: SmritiService) -> dict[str, str]:
    return {s.id: s.content_hash for s in service.snapshot().symbols if s.path != '<external>'}


def evaluate(repo: Path, revision: str, limit: int = 64) -> dict[str, object]:
    repo = repo.resolve()
    if repo == Path(__file__).resolve().parents[2]:
        raise ValueError('Run against an isolated source checkout, never the Smriti workspace')
    subprocess.run(
        ['git', '-C', str(repo), 'checkout', '--quiet', '--detach', revision], check=True
    )
    _clean(repo)
    moves: list[dict[str, object]] = []
    identifiers: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as state:
        service = SmritiService(repo, Config(repo, Path(state) / 'index'))
        service.index()
        probes = select_probes(service.snapshot().symbols, limit)
        paths = {s.id: s.path for s in service.snapshot().symbols}
        spans = {s.id: s for s in service.snapshot().symbols}
        store = MemoryStore(Path(state) / 'memory.sqlite')
        try:
            inject(store, probes, revision)
            by_path: dict[str, list[str]] = {}
            for probe in probes:
                by_path.setdefault(paths[probe.symbol_id], []).append(probe.fact_id)
            for path, facts in sorted(by_path.items()):
                source = repo / path
                target = source.with_name('moved_' + source.name)
                before = _hashes(service)
                source.rename(target)
                try:
                    service.index()
                    after = _hashes(service)
                    renames = identical_renames(before, after)
                    store.refresh(after, renames=renames, commit=revision)
                    moved_path = target.relative_to(repo).as_posix()
                    current = {s.id: s.path for s in service.snapshot().symbols}
                    for fact in (f for f in store.recall() if f.id in facts):
                        anchor = fact.anchors[0].symbol_id
                        moves.append(
                            {
                                'fact_id': fact.id,
                                'from': path,
                                'to': moved_path,
                                'freshness': fact.freshness,
                                'survived': fact.freshness == 'fresh'
                                and current.get(anchor) == moved_path,
                            }
                        )
                finally:
                    target.rename(source)
                service.index()
                store.refresh(_hashes(service), renames=identical_renames(after, _hashes(service)))
                for identity in facts:
                    store.revalidate(identity, _hashes(service), commit=revision)
            for probe in probes:
                path = repo / paths[probe.symbol_id]
                original = path.read_bytes()
                name = probe.qualname.rsplit('.', 1)[-1]
                # Rename inside the probed symbol's own byte range: a file can
                # define several methods with the same name in different classes.
                symbol = spans[probe.symbol_id]
                span, count = re.subn(
                    rb'(\bdef\s+)' + re.escape(name.encode()) + rb'\b',
                    rb'\1' + name.encode() + b'_renamed',
                    original[symbol.start_byte : symbol.end_byte],
                    count=1,
                )
                if not count:
                    continue
                renamed = original[: symbol.start_byte] + span + original[symbol.end_byte :]
                before = _hashes(service)
                path.write_bytes(renamed)
                try:
                    service.index()
                    after = _hashes(service)
                    store.refresh(after, renames=identical_renames(before, after), commit=revision)
                    fact = next(f for f in store.recall() if f.id == probe.fact_id)
                    identifiers.append(
                        {
                            'fact_id': probe.fact_id,
                            'qualname': probe.qualname,
                            'freshness': fact.freshness,
                            'conservative': fact.freshness != 'fresh',
                        }
                    )
                finally:
                    path.write_bytes(original)
                service.index()
                restored = _hashes(service)
                store.refresh(restored, renames=identical_renames(after, restored))
                store.revalidate(probe.fact_id, restored, commit=revision)
        finally:
            store.close()
    _clean(repo)
    survived = sum(bool(row['survived']) for row in moves)
    conservative = sum(bool(row['conservative']) for row in identifiers)
    return {
        'schema_version': 1,
        'revision': revision,
        'probes': len(probes),
        'file_moves': {
            'eligible_events': len(moves),
            'survived': survived,
            'rate': survived / len(moves) if moves else None,
        },
        'identifier_renames': {
            'events': len(identifiers),
            'flagged_not_fresh': conservative,
            'rate': conservative / len(identifiers) if identifiers else None,
            'note': 'Body text changes, so the anchor hash cannot verify the rename; '
            'not-fresh is the intended conservative outcome.',
        },
        'move_events': moves,
        'identifier_events': identifiers,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.smriti/replay/requests'))
    parser.add_argument('--revision', default='611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60')
    parser.add_argument(
        '--output', type=Path, default=Path('bench/codemem/results/rename_survival.json')
    )
    parser.add_argument('--probes', type=int, default=64)
    args = parser.parse_args()
    result = evaluate(args.repo, args.revision, args.probes)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if not k.endswith('_events')}, indent=2))


if __name__ == '__main__':
    main()
