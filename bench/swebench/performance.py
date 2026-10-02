"""Real checkout cold-index and reversible one-line incremental measurements."""

import argparse
import json
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from bench.swebench.datasets import ROOT
from bench.swebench.hardware import hardware_metadata, process_rss_bytes
from bench.swebench.validation import validate_checkout
from smriti.config import Config
from smriti.server.service import SmritiService


class PeakRSS:
    """Sample actual resident memory; interval is reported, not an OS exact peak."""

    def __init__(self, interval=0.01):
        self.interval = interval
        self.samples = []
        self.stop = threading.Event()

    def observe(self):
        while not self.stop.is_set():
            self.samples.append(process_rss_bytes())
            self.stop.wait(self.interval)

    def __enter__(self):
        self.thread = threading.Thread(target=self.observe, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.samples.append(process_rss_bytes())
        self.stop.set()
        self.thread.join()

    def result(self):
        samples = [value for value in self.samples if value is not None]
        return {
            'sampled_peak_rss_bytes': max(samples, default=None),
            'samples': len(samples),
            'interval_seconds': self.interval,
        }


def measure(checkout: Path, commit: str, source: str, repetitions: int = 5):
    if repetitions < 1:
        raise ValueError('At least one incremental repetition is required')
    checkout = checkout.resolve()
    if not checkout.is_relative_to((ROOT / '.smriti/evaluation/checkouts').resolve()):
        raise ValueError('Performance mutation requires an isolated benchmark checkout')
    validate_checkout(checkout, commit, source)
    state = ROOT / '.smriti/evaluation/performance' / uuid.uuid4().hex
    service = SmritiService(checkout, Config(checkout, state))
    started = time.perf_counter()
    with PeakRSS() as memory:
        cold = service.index()
    cold_seconds = time.perf_counter() - started
    snapshot = service.snapshot()
    candidates = sorted(
        {s.path for s in snapshot.symbols if s.path.endswith('.py') and s.path != '<external>'}
    )
    if not candidates:
        raise ValueError('No parsed Python source for one-line edit measurement')
    file = (checkout / candidates[0]).resolve()
    if not file.is_relative_to(checkout) or file.is_symlink():
        raise ValueError('Unsafe source edit path')
    original = file.read_bytes()
    observations = []
    try:
        for repetition in range(repetitions):
            # Appending a comment preserves encoding declarations and semantics.
            file.write_bytes(original + f'\n# Smriti incremental benchmark {repetition}\n'.encode())
            started = time.perf_counter()
            changed = service.index()
            elapsed = time.perf_counter() - started
            observations.append(
                {
                    'seconds': elapsed,
                    'index': asdict(changed),
                    'process_rss_bytes': process_rss_bytes(),
                }
            )
            if changed.changed_files != 1:
                raise AssertionError('Expected exactly one changed source file')
            file.write_bytes(original)
            service.index()
    finally:
        file.write_bytes(original)
    validate_checkout(checkout, commit, source)
    return {
        'source': source,
        'base_commit': commit,
        'hardware': hardware_metadata(),
        'cold_index_seconds': cold_seconds,
        'cold_index_memory': memory.result(),
        'cold_index': asdict(cold),
        'edited_path': candidates[0],
        'incremental_observations': observations,
        'note': 'Production end-to-end incremental index includes full resolution and snapshot persistence; this is not Merkle-only latency.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('commit')
    parser.add_argument('source')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=20)
    args = parser.parse_args()
    result = measure(args.checkout, args.commit, args.source, args.repetitions)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
