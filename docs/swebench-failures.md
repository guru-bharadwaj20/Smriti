# SWE-bench failures, misses and uncertainty

Configuration `691031a0…5b21`, held-out split (516 tasks with function gold)
unless stated. Source: `bench/swebench/results/report.json` and the raw rows in
`bench/swebench/results/raw.jsonl`.

## Scope

All 707 unique evaluations of SWE-bench Lite ∪ Verified were attempted; 698 were
measured. The per-repository columns are held-out tasks with function gold.

| Repository | Measured | Held-out | BM25 Fn R@10 | Full Fn R@10 | No-graph Fn R@10 |
| --- | --- | --- | --- | --- | --- |
| astropy/astropy | 24 | 19 | 0.421 | 0.342 | 0.474 |
| django/django | 297 | 211 | 0.350 | 0.440 | 0.448 |
| matplotlib/matplotlib | 49 | 40 | 0.238 | 0.270 | 0.313 |
| mwaskom/seaborn | 6 | 5 | 0.400 | 0.200 | 0.200 |
| pallets/flask | 4 | 4 | 0.250 | 0.375 | 0.375 |
| psf/requests | 13 | 12 | 0.333 | 0.208 | 0.208 |
| pydata/xarray | 26 | 21 | 0.206 | 0.315 | 0.464 |
| pylint-dev/pylint | 15 | 13 | 0.285 | 0.269 | 0.231 |
| pytest-dev/pytest | 34 | 27 | 0.272 | 0.241 | 0.352 |
| scikit-learn/scikit-learn | 45 | 36 | 0.324 | 0.476 | 0.463 |
| sphinx-doc/sphinx | 57 | 40 | 0.130 | 0.188 | 0.259 |
| sympy/sympy | 128 | 88 | 0.224 | 0.301 | 0.323 |

Full trails BM25 on astropy, seaborn, requests, pylint and pytest. Several of
those have fewer than 20 held-out tasks, so the per-repository means are noisy.
Django is 41% of the held-out set and is where full gains most over BM25.

## Excluded and failed tasks

Failures stay failures; none is converted to a zero or excluded silently. No
task failed at checkout, indexing or retrieval. Nine were stopped by the
leakage guard (`bench/swebench/leakage.py`), because the problem statement
contains lines of the gold patch, so retrieval on it would be contaminated:

| Task | Stage |
| --- | --- |
| django__django-12113, -12453, -13410, -15695, -16256 | leakage |
| matplotlib__matplotlib-25287 | leakage |
| scikit-learn__scikit-learn-14710 | leakage |
| sympy__sympy-15599, -22005 | leakage |

Two crashes found early in the run were fixed and the run restarted under the
new configuration: tree-sitter text that was not valid UTF-8 (`59aecd3`), and
C++ templates in `.h` files that parse with an empty name (`4313e0f`,
matplotlib).

## Retrieval misses

On 305 of 516 held-out tasks, the full pipeline placed no gold function in its
top 10. In 214 of those 305, the correct file was in its top 10, so the miss was
choosing the function within the file. BM25 found a gold function in its top 10
on only 34 of the 305. The pattern from the earlier small run still holds: the
issue describes a user-visible symptom, while the fix is in a function whose
name shares no words with it (for example, requests-6028 reports "error 407"
with proxies, and the fix is in `prepend_scheme_if_needed`). The full list is in
`report.json` under `retrieval_misses_full_recall10_zero`.

## Uncertainty

Paired bootstrap over held-out tasks (2,000 resamples, seed 0) for the
difference in function recall@10:

| Comparison | Mean difference | 95% interval |
| --- | --- | --- |
| full − BM25 | +0.063 | [+0.030, +0.097] |
| full − exact embedding | +0.023 | [−0.011, +0.057] |
| no graph − full | +0.031 | [+0.009, +0.056] |
| exact embedding − BM25 | +0.040 | [−0.006, +0.087] |

Full beats BM25. It does not separate from exact embedding, and dropping the
graph term is better than keeping it. The last two rows were computed from the
raw rows with the report's bootstrap procedure. They are not in `report.json`.

On the 152-task validation split, the gap is smaller (no graph 0.340, full
0.336). The graph weight was tuned on 34 of those tasks, before the full run.

## Run caveats

- One run, on one Windows machine with `core.autocrlf=true`, so checkouts had
  CRLF line endings.
- Embeddings were precomputed per repository with a multithreaded encoder into
  the cache the runner reads. Vectors may differ from single-threaded ones at
  float-rounding level.
- About 40 runner processes ran at once, so latency numbers in `report.json`
  include heavy contention.
