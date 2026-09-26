"""Measured-scope summary, paired confidence intervals and explicit failures."""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

import numpy as np

from bench.swebench.datasets import ROOT


def paired_interval(rows, left, right, samples=2000, seed=0):
    """Instance-paired bootstrap of recall@10 difference; no synthetic rows."""
    differences = [
        row['results'][left]['function_recall']['10']
        - row['results'][right]['function_recall']['10']
        for row in rows
        if row['results'][left]['function_recall']['10'] is not None
        and row['results'][right]['function_recall']['10'] is not None
    ]
    if not differences:
        return {'paired_instances': 0, 'mean_difference': None, 'interval95': None}
    random = np.random.default_rng(seed)
    values = np.asarray(differences)
    means = [float(random.choice(values, len(values), replace=True).mean()) for _ in range(samples)]
    return {
        'paired_instances': len(values),
        'mean_difference': float(values.mean()),
        'interval95': np.quantile(means, [0.025, 0.975]).tolist(),
        'bootstrap_samples': samples,
        'seed': seed,
    }


def summarize(rows, failures, manifest, config_id):
    measured = {row['evaluation_id']: row for row in rows if row['configuration_id'] == config_id}
    target = {row['evaluation_id'] for row in manifest['instances']}
    report = {
        'configuration_id': config_id,
        'target_dataset_rows': manifest['dataset_rows'],
        'target_unique_evaluations': len(target),
        'measured_unique': len(measured),
        'measured_dataset_rows': sum(
            row['evaluation_id'] in measured for row in manifest['instances']
        ),
        'remaining_unique': len(target - measured.keys()),
        'failures_by_stage': dict(
            Counter(row['stage'] for row in failures if row['configuration_id'] == config_id)
        ),
        'undefined_function_gold': sum(not row['gold_functions'] for row in measured.values()),
        'splits': {},
        'note': 'Failure records never become fabricated zero-recall results. Empty gold is undefined. Dataset overlaps are paired once per exact evaluation fingerprint; splits follow instance ID globally.',
    }
    for split in ('validation', 'held_out'):
        selected = [row for row in measured.values() if row['split'] == split]
        scores = {}
        for name in (
            'grep',
            'bm25',
            'embedding_exact',
            'repo_map_style',
            'full',
            'no_vector',
            'no_graph',
            'greedy',
        ):
            values = [
                row['results'][name]['function_recall']['10']
                for row in selected
                if row['results'][name]['function_recall']['10'] is not None
            ]
            scores[name] = {
                'defined_instances': len(values),
                'mean_function_recall10': statistics.mean(values) if values else None,
            }
        latency = [row['results']['full']['rank_seconds'] for row in selected]
        report['splits'][split] = {
            'instances': len(selected),
            'methods': scores,
            'full_rank_latency_seconds': {
                'p50': float(np.quantile(latency, 0.5)) if latency else None,
                'p95': float(np.quantile(latency, 0.95)) if latency else None,
            },
            'paired_full_minus_bm25': paired_interval(selected, 'full', 'bm25'),
            'paired_full_minus_embedding': paired_interval(selected, 'full', 'embedding_exact'),
        }
    return report


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    workspace = ROOT / '.smriti/evaluation'
    metadata = json.loads((workspace / 'run-metadata.json').read_text())
    result = summarize(
        read_jsonl(workspace / 'swebench-results.jsonl'),
        read_jsonl(workspace / 'swebench-failures.jsonl'),
        json.loads((ROOT / 'bench/swebench/run_manifest.json').read_text()),
        metadata['configuration_id'],
    )
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text)
