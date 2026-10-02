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
