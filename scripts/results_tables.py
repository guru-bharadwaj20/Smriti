"""Generate docs/results.md from committed result files only.

Every number in the generated tables is read from a measured result file; nothing
is typed by hand. ``tests/test_results_tables.py`` fails if docs/results.md
differs from a fresh generation. Regenerate with ``python scripts/results_tables.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import quantiles
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs' / 'results.md'


def load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def fmt(value: float | None, digits: int = 3) -> str:
    return '—' if value is None else f'{value:.{digits}f}'


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ['| ' + ' | '.join(header) + ' |', '|' + ' --- |' * len(header)]
    lines += ['| ' + ' | '.join(row) + ' |' for row in rows]
    return '\n'.join(lines)


def codemem() -> str:
    metrics = load('bench/codemem/results/metrics.json')
    renames = load('bench/codemem/results/rename_survival.json')
    compression = load('bench/codemem/results/compression.json')
    stale, cascade = metrics['staleness'], metrics['cascade']
    rows = [
        ['Real commits replayed', str(metrics['actual_commits'])],
        ['Anchored probe facts', str(metrics['probes'])],
        ['Labelled observations', f'{stale["observations"]:,}'],
        [
            'Stale detection TP / FP / FN / TN',
            f'{stale["true_positive"]} / {stale["false_positive"]} / {stale["false_negative"]} / {stale["true_negative"]:,}',
        ],
        ['Stale detection precision', fmt(stale['precision'])],
        ['Stale detection recall', fmt(stale['recall'])],
        [
            'Anchors kept fresh through file moves',
            f'{renames["file_moves"]["survived"]}/{renames["file_moves"]["eligible_events"]}',
        ],
        [
            'Identifier renames flagged not fresh',
            f'{renames["identifier_renames"]["flagged_not_fresh"]}/{renames["identifier_renames"]["events"]}',
        ],
        ['Cascade forget exact closure', str(cascade['exact_closure']).lower()],
        [
            'Facts resurrected across branches',
            f'{len(cascade["resurrected_ids"])} of {cascade["history_branches_checked"]} branches checked',
        ],
        ['Archive compression ratio', fmt(compression['ratio'])],
        [
            'Compressed archive byte-identical after restore',
            str(compression['byte_identical']).lower(),
        ],
    ]
    return (
        '## Code-anchored memory (CodeMem)\n\n'
        f'Repository `{metrics["repository"]}`, sequence SHA-256 `{metrics["sequence_sha256"][:16]}…`.\n'
        'Sources: `bench/codemem/results/metrics.json`, `rename_survival.json`, `compression.json`.\n\n'
        + table(['Measure', 'Value'], rows)
    )


def longmemeval() -> str:
    summary = load('bench/longmemeval/results/longmemeval_s.summary.json')
    metrics = summary['metrics']
    order = ['all'] + sorted(k for k in metrics if k not in {'all', 'abstention'}) + ['abstention']
    rows = [
        [name, str(metrics[name]['questions']), fmt(metrics[name]['session_recall_at_5'])]
        for name in order
    ]
    return (
        '## Long-term memory retrieval (LongMemEval-S, retrieval only)\n\n'
        f'Dataset `{summary["manifest"]["repository"]}` @ `{summary["manifest"]["revision"][:8]}`. '
        'Answer accuracy is not measured. Source: '
        '`bench/longmemeval/results/longmemeval_s.summary.json`.\n\n'
        + table(['Question type', 'Questions', 'Session recall@5'], rows)
    )


def swebench() -> str:
    report = load('bench/swebench/results/report.json')
    split = report['splits']['held_out']
    methods = split['methods']
    names = {
        'grep': 'Substring grep',
        'bm25': 'BM25F',
        'embedding_exact': 'Exact embedding',
        'repo_map_style': 'Aider-style repo map',
        'full': 'Smriti full',
        'no_vector': 'Smriti without vectors',
        'no_graph': 'Smriti without graph',
        'greedy': 'Smriti, greedy packing',
    }
    recall = [
        [label]
        + [fmt(methods[key]['function_recall'][k]['mean']) for k in ('1', '5', '10', '20', '50')]
        + [fmt(methods[key]['file_recall']['10']['mean'])]
        for key, label in names.items()
    ]
    coverage = [
        [names[key]]
        + [
            f'{fmt(methods[key]["budget_coverage"][b]["mean_recall"])} ({methods[key]["budget_coverage"][b]["mean_tokens"]:,.0f})'
            for b in ('4096', '8192', '16384')
        ]
        for key in ('full', 'no_vector', 'no_graph', 'greedy')
    ]
    intervals = [
        [
            label,
            fmt(split[key]['mean_difference']),
            f'[{fmt(split[key]["interval95"][0])}, {fmt(split[key]["interval95"][1])}]',
        ]
        for key, label in (
            ('paired_full_minus_bm25', 'Smriti full − BM25F'),
            ('paired_full_minus_embedding', 'Smriti full − exact embedding'),
        )
    ]
    repos = ', '.join(f'{repo} {n}' for repo, n in sorted(report['measured_repositories'].items()))
    return (
        '## Code retrieval (SWE-bench Lite ∪ Verified subset)\n\n'
        f'{report["measured_unique"]} of {report["target_unique_evaluations"]} unique tasks measured '
        f'({repos}); {len(report["unresolved_failures"])} were excluded or failed and are listed in '
        '`docs/swebench-failures.md`. Held-out split: '
        f'{split["instances"]} tasks. Source: `bench/swebench/results/report.json`.\n\n'
        '### Function recall@k and file recall@10\n\n'
        + table(['Method', '@1', '@5', '@10', '@20', '@50', 'File @10'], recall)
        + '\n\n### Gold functions covered by packed context (mean tokens)\n\n'
        + table(['Method', '4,096', '8,192', '16,384'], coverage)
        + '\n\n### Paired bootstrap, function recall@10 (2,000 resamples)\n\n'
        + table(['Comparison', 'Mean difference', '95% interval'], intervals)
    )


def performance() -> str:
    perf = load('bench/swebench/results/performance.json')
    report = load('bench/swebench/results/report.json')
    native = load('bench/vector/native_profile.json')
    edits = [row['seconds'] for row in perf['incremental_observations']]
    cuts = quantiles(edits, n=100, method='inclusive')
    latency = report['splits']['held_out']['query_latency_seconds']
    rows = [
        [
            'Cold index, psf/requests (files / symbols)',
            f'{fmt(perf["cold_index_seconds"], 2)} s ({perf["cold_index"]["files"]} / {perf["cold_index"]["symbols"]:,})',
        ],
        [
            'Sampled peak RSS during cold index',
            f'{perf["cold_index_memory"]["sampled_peak_rss_bytes"] / 1e6:.1f} MB',
        ],
        [
            f'One-line edit re-index p50 / p95 ({len(edits)} runs)',
            f'{fmt(cuts[49], 2)} / {fmt(cuts[94], 2)} s',
        ],
        [
            'Full ranking p50 / p95',
            f'{fmt(latency["full"]["p50"])} / {fmt(latency["full"]["p95"])} s',
        ],
        [
            '8k knapsack packing p50 / p95',
            f'{fmt(latency["full_pack_8192"]["p50"])} / {fmt(latency["full_pack_8192"]["p95"])} s',
        ],
        ['BM25F baseline query p50', f'{fmt(latency["bm25"]["p50"])} s'],
        ['Rust distance kernel speedup (identical results)', f'{native["speedup"]:.2f}x'],
    ]
    hardware = perf['hardware']
    return (
        '## Performance\n\n'
        f'{hardware["cpu"]}, {hardware["logical_cpus"]} logical CPUs, '
        f'{hardware["ram_bytes"] / 2**30:.1f} GiB RAM, {hardware["os"]}, Python {hardware["python"]}. '
        'Sources: `bench/swebench/results/performance.json`, `report.json`, '
        '`bench/vector/native_profile.json`.\n\n' + table(['Measure', 'Value'], rows)
    )


def agent() -> str:
    result = load('bench/agent/results.json')
    summary = result['summary']
    conditions = ('baseline', 'whole_repo', 'smriti')
    row = [result['model'].split('@')[0]] + [
        f'{summary[c]["solved"]}/{summary[c]["tasks"]}' for c in conditions
    ]
    return (
        '## Coding-agent task success (optional)\n\n'
        f'Eight injected bugs, {result["context_budget_tokens"]:,}-token context. The fixture '
        'fits within the budget, so whole-repo and Smriti context are expected to tie '
        '(see `bench/agent/README.md`). Source: `bench/agent/results.json`.\n\n'
        + table(['Model', 'File list only', 'Whole repo', 'Smriti context'], [row])
    )


def generate() -> str:
    sections = [codemem(), longmemeval(), swebench(), performance(), agent()]
    return (
        '# Results\n\n'
        '<!-- Generated by scripts/results_tables.py from committed result files. Do not edit. -->\n\n'
        'Every value below is read from a measured result file. Interpretation and '
        'limitations: [report.md](report.md), [limitations.md](limitations.md).\n\n'
        + '\n\n'.join(sections)
        + '\n'
    )


if __name__ == '__main__':
    OUTPUT.write_text(generate(), encoding='utf-8', newline='\n')
    print(f'wrote {OUTPUT.relative_to(ROOT)}')
