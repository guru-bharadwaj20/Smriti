"""Resumable CPU evaluation on all pinned SWE-bench test instances.

Run ``python -m bench.swebench.runner --limit 1`` for an actual pinned smoke,
then omit --limit to continue the full 800-row/707-unique evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from dataclasses import asdict
from functools import partial

from bench.swebench.ablations import context, variant
from bench.swebench.checkout import checkout_base
from bench.swebench.datasets import ROOT, load_tasks
from bench.swebench.embedding_baseline import EmbeddingBaseline
from bench.swebench.function_metrics import function_recall_at_k
from bench.swebench.grep_baseline import grep_baseline
from bench.swebench.ground_truth import parse_changed_files
from bench.swebench.hardware import hardware_metadata, process_rss_bytes
from bench.swebench.lexical_baseline import LexicalBaseline
from bench.swebench.mapping import gold_base_functions
from bench.swebench.metrics import file_recall_at_k
from bench.swebench.repo_map_baseline import repo_map_baseline
from bench.swebench.splits import instance_split
from bench.swebench.validation import validate_checkout
from smriti.config import Config
from smriti.server.retrieval import Retriever
from smriti.server.service import SmritiService
from smriti.vector.embedding import BatchedEmbedder, EmbeddingCache, ONNXEmbedder

BUDGETS = (4096, 8192, 16384)
KS = (1, 5, 10, 20, 50)


def verify_artifacts(manifest):
    for info in manifest.values():
        for artifact in info['artifacts']:
            path = (ROOT / artifact['path']).resolve()
            if not path.is_relative_to((ROOT / 'bench/data').resolve()):
                raise ValueError('Artifact escaped ignored benchmark data root')
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != artifact['sha256']:
                raise ValueError(f'Changed dataset artifact: {path}')


def measure_ranks(ids, symbols, gold, files):
    by_id = {symbol.id: symbol for symbol in symbols}
    paths = [by_id[id].path for id in ids if id in by_id]
    return {
        'function_recall': {str(k): function_recall_at_k(ids, gold, k) for k in KS},
        'file_recall': {str(k): file_recall_at_k(paths, files, k) for k in KS},
    }


def append(path, record):
    with path.open('a', encoding='utf-8') as output:
        output.write(json.dumps(record, sort_keys=True) + '\n')
        output.flush()
        os.fsync(output.fileno())


def run(limit=None, repo_filter=None):
    artifacts = json.loads((ROOT / 'bench/swebench/dataset_artifacts.json').read_text())
    verify_artifacts(artifacts)
    tasks = load_tasks(artifacts)
    unique = {task.evaluation_id: task for task in tasks}
    workspace = ROOT / '.smriti/evaluation'
    workspace.mkdir(parents=True, exist_ok=True)
    output = workspace / 'swebench-results.jsonl'
    failures = workspace / 'swebench-failures.jsonl'
    model = ROOT / '.smriti/models'
    encoder = EmbeddingCache(
        workspace / 'embeddings.sqlite',
        BatchedEmbedder(ONNXEmbedder(model / 'model.onnx', model / 'tokenizer.json')),
    )
    configuration = {
        'model': encoder.version,
        'budgets': BUDGETS,
        'k': KS,
        'pipeline_version': 1,
        'source_fingerprint': hashlib.sha256(
            b''.join(
                file.relative_to(ROOT).as_posix().encode() + b'\0' + file.read_bytes()
                for directory in ('smriti', 'bench/swebench')
                for file in sorted((ROOT / directory).rglob('*.py'))
            )
        ).hexdigest(),
        'split': 'sha256-instance-mod5',
        'seed': 0,
        'ANN': {'m': 16, 'ef_construction': 100, 'ef_search': 50},
    }
    config_id = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()
    metadata = {
        'configuration': configuration,
        'configuration_id': config_id,
        'hardware': hardware_metadata(),
        'dataset_rows': len(tasks),
        'unique_evaluations': len(unique),
        'engine_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
    }
    (workspace / 'run-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    completed = set()
    if output.exists():
        for line in output.read_text().splitlines():
            row = json.loads(line)
            if row['configuration_id'] == config_id:
                completed.add(row['evaluation_id'])
    services = {}
    last_build = {}
    measured = 0
    attempted = 0
    try:
        for identity, task in sorted(
            unique.items(), key=lambda item: (item[1].repo, item[1].base_commit, item[0])
        ):
            if identity in completed or (repo_filter and task.repo != repo_filter):
                continue
            if limit is not None and attempted >= limit:
                break
            attempted += 1
            stage = 'checkout'
            started = time.perf_counter()
            print(
                json.dumps({'stage': stage, 'evaluation_id': identity, 'repo': task.repo}),
                flush=True,
            )
            try:
                slug = task.repo.replace('/', '--')
                checkout = workspace / 'checkouts' / slug
                source = 'https://github.com/' + task.repo + '.git'
                if not checkout.exists():
                    checkout_base(source, task.base_commit, checkout)
                else:
                    subprocess.run(
                        ['git', '-C', str(checkout), 'checkout', '--detach', task.base_commit],
                        check=True,
                        capture_output=True,
                        timeout=120,
                    )
                validate_checkout(checkout, task.base_commit, source)
                stage = 'index'
                state = workspace / 'states' / slug
                if slug not in services:
                    services[slug] = SmritiService(checkout, Config(checkout, state))
                service = services[slug]
                tick = time.perf_counter()
                indexed = service.index()
                index_seconds = time.perf_counter() - tick
                snapshot = service.snapshot()
                symbols = [s for s in snapshot.symbols if s.path != '<external>']
                stage = 'ground_truth'
                changes = parse_changed_files(task.patch)
                gold = gold_base_functions(changes, symbols)
                gold_files = {change.old_path for change in changes if change.old_path}
                stage = 'retrieval_build'
                print(
                    json.dumps(
                        {
                            'stage': stage,
                            'evaluation_id': identity,
                            'symbols': len(symbols),
                            'index_seconds': index_seconds,
                        }
                    ),
                    flush=True,
                )
                build_key = (slug, snapshot.version)
                if build_key not in last_build:
                    tick = time.perf_counter()
                    full = Retriever(snapshot, state_dir=state, encoder=encoder)
                    lexical = LexicalBaseline(symbols)
                    semantic = EmbeddingBaseline(symbols, encoder)
                    last_build.clear()  # Bound active dense matrices and ANN graphs on an 8GB CPU machine.
                    last_build[build_key] = (full, lexical, semantic, time.perf_counter() - tick)
                full, lexical, semantic, build_seconds = last_build[build_key]
                stage = 'query'
                results = {}
                baseline_functions = {
                    'grep': partial(grep_baseline, symbols, task.problem_statement),
                    'bm25': partial(lexical.search, task.problem_statement),
                    'embedding_exact': partial(semantic.search, task.problem_statement),
                    'repo_map_style': partial(
                        repo_map_baseline, symbols, snapshot.edges, task.problem_statement
                    ),
                }
                for name, search in baseline_functions.items():
                    tick = time.perf_counter()
                    hits = search()
                    result = measure_ranks([hit.id for hit in hits], symbols, gold, gold_files)
                    result['query_seconds'] = time.perf_counter() - tick
                    results[name] = result
                for name in ('full', 'no_vector', 'no_graph', 'greedy'):
                    tick = time.perf_counter()
                    ranks = variant(full, name).rank(task.problem_statement)
                    result = measure_ranks(list(ranks), symbols, gold, gold_files)
                    result['rank_seconds'] = time.perf_counter() - tick
                    result['budgets'] = {}
                    covered_budgets = []
                    for budget in BUDGETS:
                        tick = time.perf_counter()
                        packed = context(full, name, task.problem_statement, budget)
                        recall = len(set(packed.covered_ids) & gold) / len(gold) if gold else None
                        if packed.token_count > budget:
                            raise AssertionError(
                                'Production context exceeded actual tokenizer budget'
                            )
                        result['budgets'][str(budget)] = {
                            'tokens': packed.token_count,
                            'function_recall': recall,
                            'seconds': time.perf_counter() - tick,
                        }
                        if recall == 1:
                            covered_budgets.append(budget)
                    result['minimum_tested_budget_covering_gold'] = min(
                        covered_budgets, default=None
                    )
                    results[name] = result
                record = {
                    'evaluation_id': identity,
                    'instance_id': task.instance_id,
                    'repo': task.repo,
                    'base_commit': task.base_commit,
                    'split': instance_split(task.instance_id),
                    'configuration_id': config_id,
                    'symbols': len(symbols),
                    'edges': len(snapshot.edges),
                    'gold_functions': len(gold),
                    'gold_files': len(gold_files),
                    'index': asdict(indexed),
                    'index_seconds': index_seconds,
                    'retrieval_build_seconds': build_seconds,
                    'process_rss_bytes': process_rss_bytes(),
                    'total_seconds': time.perf_counter() - started,
                    'results': results,
                }
                append(output, record)
                completed.add(identity)
                measured += 1
                print(
                    json.dumps(
                        {
                            'stage': 'complete',
                            'evaluation_id': identity,
                            'seconds': record['total_seconds'],
                        }
                    ),
                    flush=True,
                )
            except Exception as error:
                append(
                    failures,
                    {
                        'evaluation_id': identity,
                        'configuration_id': config_id,
                        'stage': stage,
                        'error': repr(error),
                    },
                )
                print(
                    json.dumps(
                        {'stage': 'failure', 'evaluation_id': identity, 'error': repr(error)}
                    ),
                    flush=True,
                )
    finally:
        encoder.close()
    return {
        'completed_unique': len(completed),
        'target_unique': len(unique),
        'newly_measured': measured,
        'dataset_rows': len(tasks),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--repo')
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.limit, arguments.repo), indent=2))
