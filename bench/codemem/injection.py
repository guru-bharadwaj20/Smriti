"""Deterministic code-fingerprint probe injection into real repository snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from hashlib import sha256

from smriti.memory import Anchor, MemoryStore
from smriti.models import Symbol


@dataclass(frozen=True)
class Probe:
    fact_id: str
    symbol_id: str
    path: str
    qualname: str
    content_hash: str


def select_probes(symbols: Iterable[Symbol], limit: int = 64) -> tuple[Probe, ...]:
    if limit < 1:
        raise ValueError('Probe limit must be positive')
    candidates = [
        s
        for s in symbols
        if s.kind in ('function', 'method')
        and s.path.startswith(('src/requests/', 'requests/'))
        and s.content_hash
    ]
    candidates.sort(key=lambda s: (sha256(s.id.encode()).hexdigest(), s.id))
    if not candidates:
        raise ValueError('No Requests library function symbols available')
    return tuple(
        Probe(
            'probe-' + sha256(s.id.encode()).hexdigest()[:24],
            s.id,
            s.path,
            s.qualname,
            s.content_hash,
        )
        for s in candidates[:limit]
    )


def inject(store: MemoryStore, probes: Iterable[Probe], commit: str) -> None:
    for probe in probes:
        store.remember(
            'Implementation fingerprint for ' + probe.qualname + ': ' + probe.content_hash,
            fact_id=probe.fact_id,
            anchors=[Anchor(probe.symbol_id, probe.content_hash)],
            source='code',
            session='codemem/' + commit,
            tool='codemem',
            subject=probe.symbol_id,
        )


def fixture(probes: Iterable[Probe], commit: str) -> dict[str, object]:
    return {
        'schema_version': 1,
        'initial_commit': commit,
        'policy': 'Deterministic SHA256-ranked library functions; facts assert implementation fingerprints, not semantic claims.',
        'probes': [asdict(p) for p in probes],
    }
