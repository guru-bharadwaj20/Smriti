# Performance

All measurements: Intel Core i3-5005U (2 cores, 4 threads, 2.0 GHz), 8 GB RAM,
Windows 11, Python 3.13.1, pure-Python engine (optional Rust kernel not used),
lexical + vector retrieval with the pinned int8 MiniLM model. One run each; no
other benchmark workload was running.

## Indexing (P13.35, P13.36)

Source: `bench/swebench/results/performance.json`, psf/requests at
`36453b95` (98 Python files, 2,487 symbols), state outside the checkout.

| Measurement | Value |
| --- | --- |
| Cold index (scan, parse, resolve, publish) | 10.86 s |
| Sampled peak resident memory during cold index | 91.8 MB (316 samples at 10 ms) |
| One-line edit, re-index, p50 (20 repetitions) | 9.64 s |
| One-line edit, re-index, p95 | 10.12 s |

Each repetition appends a comment to one file, re-indexes (exactly one changed
file every time) and restores it. Only that file is re-parsed, but resolution and
snapshot publication still process the whole repository, so an incremental
update costs about 90% of a cold index here. The earlier 0.21 s figure in
`docs/demo.md` was a 20-file demo repository. Making resolution and publication
incremental per changed file is the main performance gap.

## Query latency (P13.37)

Measured on the earlier 16-task run (configuration `559fae87…`); the full
698-task run ran about 40 processes in parallel, so its latencies in
`bench/swebench/results/report.json` include contention and are not used here.
Held-out split, 15 real SWE-bench
issue queries against requests and flask (588–1,629 indexed symbols), warm
in-process indexes. Ranking excludes index construction; packing includes
rendering and the final tokenizer recount.

| Method | p50 (s) | p95 (s) |
| --- | --- | --- |
| BM25 baseline | 0.024 | 0.055 |
| Exact embedding baseline | 0.006 | 0.287 |
| Substring grep baseline | 0.105 | 0.245 |
| Aider-style repo map baseline | 0.546 | 1.875 |
| Full ranking (BM25F + HNSW + RRF + PageRank) | 0.642 | 1.997 |
| Full ranking without graph | 0.064 | 0.155 |
| Full ranking without vectors | 0.638 | 1.760 |
| Pack 8,192 tokens, knapsack (after ranking) | 4.277 | 6.888 |
| Pack 8,192 tokens, greedy (after ranking) | 0.863 | 2.272 |

Personalized PageRank accounts for nearly all ranking time (0.64 s vs 0.06 s
without it) and the knapsack dominates end-to-end latency: about 5 s at p50 for
an 8k-token context on this laptop. Greedy packing is 5x faster and reached the
same mean coverage (0.567) on these tasks.
