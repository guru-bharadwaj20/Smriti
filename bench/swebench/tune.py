"""Tune the PageRank graph weight on SWE-bench validation tasks only.

Held-out instances are refused. For every validation task the production
retriever computes its candidate lists and graph scores once; each candidate
weight then only re-combines them, so all weights see identical inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

from bench.swebench.checkout import checkout_base
from bench.swebench.datasets import ROOT, load_tasks
from bench.swebench.function_metrics import function_recall_at_k
from bench.swebench.ground_truth import parse_changed_files
from bench.swebench.leakage import assert_no_leakage
from bench.swebench.mapping import gold_base_functions
from bench.swebench.metrics import file_recall_at_k
from bench.swebench.splits import instance_split
from bench.swebench.validation import validate_checkout
from smriti.config import Config
from smriti.server.retrieval import Retriever
from smriti.server.service import SmritiService
from smriti.vector.embedding import BatchedEmbedder, EmbeddingCache, ONNXEmbedder

WEIGHTS = (0.0, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 1.0)


def evaluate(
    repos: list[str],
    output: Path,
    workspace: Path | None = None,
    shard: tuple[int, int] | None = None,
) -> dict[str, object]:
    artifacts = json.loads((ROOT / 'bench/swebench/dataset_artifacts.json').read_text())
    tasks = {t.evaluation_id: t for t in load_tasks(artifacts)}
    selected = sorted(
        (
            t
            for t in tasks.values()
            if t.repo in repos and instance_split(t.instance_id) == 'validation'
        ),
        key=lambda t: (t.repo, t.base_commit, t.evaluation_id),
    )
    if any(instance_split(t.instance_id) != 'validation' for t in selected):
        raise AssertionError('Held-out task selected for tuning')
    if shard is not None:
        size = -(-len(selected) // shard[1])
        selected = selected[shard[0] * size : (shard[0] + 1) * size]
    workspace = workspace or ROOT / '.smriti/evaluation'
    workspace.mkdir(parents=True, exist_ok=True)
    model = ROOT / '.smriti/models'
    encoder = EmbeddingCache(
        workspace / 'embeddings.sqlite',
        BatchedEmbedder(ONNXEmbedder(model / 'model.onnx', model / 'tokenizer.json')),
    )
    done: dict[str, dict[str, object]] = {}
    if output.exists():
        for line in output.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            done[row['evaluation_id']] = row
    services: dict[str, SmritiService] = {}
    with output.open('a', encoding='utf-8') as stream:
        for task in selected:
            if task.evaluation_id in done:
                continue
            started = time.perf_counter()
            slug = task.repo.replace('/', '--')
            checkout = workspace / 'checkouts' / slug
            source = f'https://github.com/{task.repo}.git'
            try:
                if not checkout.exists():
                    checkout_base(source, task.base_commit, checkout)
                else:
                    import subprocess

                    subprocess.run(
                        ['git', '-C', str(checkout), 'checkout', '--detach', task.base_commit],
                        check=True,
                        capture_output=True,
                        timeout=120,
                    )
                validate_checkout(checkout, task.base_commit, source)
                state = workspace / 'states' / slug
                service = services.setdefault(
                    slug, SmritiService(checkout, Config(checkout, state))
                )
                service.index()
                snapshot = service.snapshot()
                symbols = [s for s in snapshot.symbols if s.path != '<external>']
                changes = parse_changed_files(task.patch)
                gold = gold_base_functions(changes, symbols)
                files = {c.old_path for c in changes if c.old_path}
                assert_no_leakage(task.problem_statement, task.patch, checkout, symbols)
                retriever = Retriever(snapshot, state_dir=state, encoder=encoder)
                parts = retriever.components(task.problem_statement)
                paths = {s.id: s.path for s in symbols}
                scores = {}
                for weight in WEIGHTS:
                    ranked = list(retriever.combine(parts, weight))
                    scores[str(weight)] = {
                        'function_recall10': function_recall_at_k(ranked, gold, 10),
                        'function_recall5': function_recall_at_k(ranked, gold, 5),
                        'file_recall10': file_recall_at_k(
                            [paths[i] for i in ranked if i in paths], files, 10
                        ),
                    }
                row = {
                    'evaluation_id': task.evaluation_id,
                    'repo': task.repo,
                    'split': 'validation',
                    'gold_functions': len(gold),
                    'scores': scores,
                    'seconds': time.perf_counter() - started,
                }
            except Exception as error:  # recorded, never scored
                row = {'evaluation_id': task.evaluation_id, 'repo': task.repo, 'error': repr(error)}
            done[task.evaluation_id] = row
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            stream.flush()
            print(json.dumps({k: row[k] for k in row if k != 'scores'}), flush=True)
    scored = [r for r in done.values() if 'scores' in r and r['gold_functions']]
    summary = {}
    for weight in WEIGHTS:
        key = str(weight)
        summary[key] = {
            metric: statistics.mean(r['scores'][key][metric] for r in scored) if scored else None
            for metric in ('function_recall10', 'function_recall5', 'file_recall10')
        }
    best = max(
        WEIGHTS,
        key=lambda w: (
            summary[str(w)]['function_recall10'] or 0,
            summary[str(w)]['function_recall5'] or 0,
            -w,
        ),
    )
    return {
        'schema_version': 1,
        'repositories': repos,
        'validation_tasks_scored': len(scored),
        'failures': [r for r in done.values() if 'error' in r],
        'weights': summary,
        'selected_graph_weight': best,
        'selection_rule': 'max function recall@10, then recall@5, then smaller weight',
        'task_ids_sha256': hashlib.sha256(
            '\n'.join(sorted(r['evaluation_id'] for r in scored)).encode()
        ).hexdigest(),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', action='append', required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'bench/swebench/results/tuning.jsonl')
    parser.add_argument('--workspace', type=Path, help='Separate checkout and cache directory')
    parser.add_argument('--shard', help='K/N: tune the K-th (0-based) of N contiguous slices')
    args = parser.parse_args()
    shard = tuple(int(part) for part in args.shard.split('/')) if args.shard else None
    result = evaluate(args.repo, args.output, args.workspace, shard)
    args.output.with_suffix('.summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'failures'}, indent=2))
