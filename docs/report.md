# Smriti project report

## Summary

Smriti is a local, CPU-only memory and context engine for coding agents, exposed over MCP. It indexes a repository incrementally, parses six languages with tree-sitter, builds a scope-aware call graph, retrieves code with lexical, vector and graph signals, packs the result into a strict token budget, and keeps a code-anchored memory whose facts are marked fresh, stale or orphaned as the code changes. Replayed over 200 real psf/requests commits with 64 probe facts, the memory layer detected staleness with precision and recall of 1.0 across 12,736 observations, and cascading forget removed exactly the expected closure of facts with no resurrection across 201 history branches. On LongMemEval-S (retrieval only, no answer generation), session recall@5 was 0.848 over 500 questions. On the 15 held-out SWE-bench tasks measured so far, the full retrieval pipeline does not beat BM25 on function recall@10 (0.267 vs 0.333; the paired interval includes zero), although its file recall@10 is higher (0.933 vs 0.867). A one-line edit still costs about 9.6 s to re-index on requests because resolution and snapshot publication are whole-repository. In short: the memory freshness design holds up well under test, the ranking stack is not yet better than a plain BM25 baseline on this small subset, and incremental indexing is the main performance gap.

Every table below is also generated mechanically from the result files in [results.md](results.md).

## System

The pipeline is described in [architecture.md](architecture.md). In brief:

1. A Merkle scanner hashes files bottom-up and reparses only changed leaves.
2. tree-sitter extracts symbols for Python, TypeScript, Java, Go, C and C++, reusing previous trees for edited files.
3. A resolver builds scope chains and emits `defines`, `contains`, `calls`, `may_call`, `imports`, `inherits` and `tests` edges with confidence weights. Python has the deepest resolution (see [limitations.md](limitations.md)).
4. Each index run publishes an immutable snapshot atomically, so queries always read one complete version.
5. Retrieval combines BM25F and a custom HNSW index with reciprocal rank fusion, expands candidates with personalized PageRank over the graph, and packs symbol representations with a multiple-choice knapsack under a tokenizer budget.
6. Memory is a separate, content-addressed operation log. Facts are anchored to symbol hashes and refreshed after every index. The store is bitemporal, supports git-like branches, merges and revert, and implements cascading, irreversible forget. Exported sync bundles are authenticated with HMAC. Semantics are in [memory-semantics.md](memory-semantics.md); related systems are discussed in [prior-work.md](prior-work.md).

The CLI, MCP server and UI call the same service methods, and a test checks that they return identical results. An optional Rust kernel, a VS Code extension (`vscode/`) and a Docker image ([docker.md](docker.md)) are included.

## Evaluation setup

All measurements come from a single machine and a single run: Intel Core i3-5005U at 2.0 GHz, 4 logical CPUs, 8 GB RAM, Windows 11 (build 22000), Python 3.13.1. The timings reflect a low-end laptop and were not repeated on other machines.

| Dataset | Pinned revision | Use |
| --- | --- | --- |
| psf/requests | 200 first-parent commits ending at `611c6162`, sequence SHA-256 `6564447e…6609` | CodeMem replay and rename test |
| xiaowu0162/longmemeval-cleaned, `longmemeval_s_cleaned.json` | `98d7416c24c778c2fee6e6f3006e7a073259d48f` | Session retrieval |
| princeton-nlp/SWE-bench_Lite (test) | `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2` | Code retrieval |
| princeton-nlp/SWE-bench_Verified (test) | `c104f840cc67f8b6eec6f759ebc8b2693d585d4a` | Code retrieval |
| psf/requests for performance | `36453b95b13079296776d11b09cab2567ea3e703` (98 files, 2,487 symbols) | Indexing latency |

Sources: `bench/codemem/results/metrics.json`, `bench/codemem/results/rename_survival.json`, `bench/longmemeval/results/longmemeval_s.summary.json`, `bench/datasets.json`, `bench/swebench/results/performance.json`.

## Results: code-anchored memory (CodeMem)

CodeMem ([bench/codemem/README.md](../bench/codemem/README.md)) replays real history without an LLM. 64 probe facts are anchored to symbols, the 200 commits are applied in order, and at each step the system's freshness verdict is compared with a structural label derived independently from indexed hashes: did the anchored implementation change, or did the symbol disappear? Labels describe code changes, not whether a natural-language claim is still true.

| Staleness detection | Value |
| --- | --- |
| Observations | 12,736 |
| True positives | 87 |
| False positives | 0 |
| True negatives | 12,649 |
| False negatives | 0 |
| Precision | 1.0 |
| Recall | 1.0 |

Source: `bench/codemem/results/metrics.json`.

The replayed history contained no eligible rename events, so rename survival was measured separately by applying real moves and renames to all 64 probes at the pinned revision.

| Rename test | Events | Outcome | Rate |
| --- | --- | --- | --- |
| File moves, identical content | 64 | 64 stayed fresh | 1.0 |
| Identifier renames | 64 | 64 flagged not fresh | 1.0 |

Source: `bench/codemem/results/rename_survival.json`. An identifier rename changes the body text, so the anchor hash cannot confirm identity; marking these not fresh is the intended conservative outcome, and it also means renamed symbols are not tracked.

Cascading forget removed exactly the four expected facts (one probe and three derived facts forming a diamond), with no resurrected IDs across 201 history branches, and the operation log verified afterwards (`metrics.json`). Lossless zlib compression of the authenticated memory archive reduced 379,929 bytes to 79,465 (ratio 0.209); the output was byte-identical and still authenticated after decompression (`bench/codemem/results/compression.json`).

## Results: long-term memory retrieval (LongMemEval-S)

This is session retrieval only: for each question, does a gold session appear in the top five retrieved sessions? No answers are generated, so these numbers are not comparable to answer-accuracy results. Fact search is lexical (BM25). Details in [longmemeval.md](longmemeval.md).

| Category | Questions | Session recall@5 |
| --- | --- | --- |
| All | 500 | 0.848 |
| single-session-user | 70 | 0.986 |
| single-session-assistant | 56 | 1.000 |
| single-session-preference | 30 | 0.867 |
| knowledge-update | 78 | 0.968 |
| multi-session | 133 | 0.830 |
| abstention | 30 | 0.756 |
| temporal-reasoning | 133 | 0.655 |

Source: `bench/longmemeval/results/longmemeval_s.summary.json`. Temporal reasoning is the weakest category, as expected from lexical retrieval without date reasoning. The abstention retrieval rate was 0.0; abstention is implemented as empty retrieval, not a model judgement.

## Results: code retrieval on SWE-bench

The target was 707 unique evaluations (800 dataset rows across Lite and Verified). Only 16 were measured: 12 from psf/requests and 4 from pallets/flask. All six seaborn tasks failed at `git clone` because the network was unavailable, and requests-1724 failed while building retrieval state with a Windows `PermissionError` on rename. Failures are recorded, never scored as zero ([swebench-failures.md](swebench-failures.md)). Before every task, a leakage check confirmed that the query contained no patch text and the index contained no post-fix lines. The validation split has one task and is not interpreted. The numbers below are the held-out split, 15 tasks; retrieval input is the problem statement, and gold functions and files come from the patch.

| Method | Fn R@1 | Fn R@5 | Fn R@10 | Fn R@20 | Fn R@50 | File R@1 | File R@5 | File R@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grep | 0.000 | 0.000 | 0.000 | 0.000 | 0.133 | 0.000 | 0.933 | 1.000 |
| BM25 | 0.167 | 0.167 | 0.333 | 0.333 | 0.433 | 0.467 | 0.867 | 0.867 |
| embedding (exact) | 0.267 | 0.333 | 0.333 | 0.433 | 0.467 | 0.400 | 0.733 | 0.800 |
| repo-map style | 0.000 | 0.000 | 0.067 | 0.067 | 0.333 | 0.067 | 0.333 | 0.533 |
| Smriti full | 0.000 | 0.233 | 0.267 | 0.300 | 0.567 | 0.200 | 0.800 | 0.933 |
| full, no vector | 0.067 | 0.167 | 0.267 | 0.333 | 0.433 | 0.267 | 0.867 | 0.933 |
| full, no graph | 0.200 | 0.267 | 0.267 | 0.433 | 0.567 | 0.400 | 0.867 | 0.933 |
| full, greedy packing | 0.000 | 0.233 | 0.267 | 0.300 | 0.567 | 0.200 | 0.800 | 0.933 |

Source: `bench/swebench/results/report.json`, `splits.held_out.methods`.

Packed-budget coverage is the mean fraction of gold functions included in the packed context.

| Method | 4k tokens | 8k tokens | 16k tokens |
| --- | --- | --- | --- |
| full | 0.433 | 0.567 | 0.567 |
| no vector | 0.267 | 0.400 | 0.433 |
| no graph | 0.400 | 0.633 | 0.633 |
| greedy | 0.433 | 0.567 | 0.567 |

Source: `bench/swebench/results/report.json`, `budget_coverage`.

| Paired bootstrap, function recall@10 (2,000 samples, seed 0) | Mean difference | 95% interval |
| --- | --- | --- |
| full minus BM25 | −0.067 | [−0.233, 0.067] |
| full minus exact embedding | −0.067 | [−0.300, 0.100] |

Source: `bench/swebench/results/report.json`, `paired_full_minus_*`.

The full pipeline does not beat BM25 on function recall@10 on this subset (0.267 vs 0.333), and the interval includes zero, so 15 tasks cannot separate the two in either direction. Full does have higher file recall@10 (0.933 vs 0.867) and higher function recall@50 (0.567 vs 0.433): it finds the right file but ranks the exact function too low. In 10 of 15 tasks full had zero function recall@10, and in 9 of those the right file was in its top 10.

The ablations point in different directions. Removing vectors lowers 8k coverage from 0.567 to 0.400, so the embedding signal contributes. Removing the graph raises 8k coverage to 0.633 and improves early function recall (R@1 0.200 vs 0.000): on these tasks, personalized PageRank expansion pushes gold functions down. Exact knapsack and greedy packing give identical coverage here. With 15 tasks from two repositories, none of these differences is statistically established.

## Performance

| Measurement | Value |
| --- | --- |
| Cold index, requests (98 files, 2,487 symbols) | 10.86 s |
| Sampled peak RSS during cold index | 91.8 MB |
| One-line edit re-index, p50 (20 runs) | 9.64 s |
| One-line edit re-index, p95 | 10.12 s |

Source: `bench/swebench/results/performance.json`, [performance.md](performance.md). Each incremental run changes exactly one file and only that file is reparsed, but resolution and snapshot publication still process the whole repository, so an incremental update costs about 90% of a cold index.

Query latency on the 15 held-out tasks:

| Method | p50 (s) | p95 (s) |
| --- | --- | --- |
| grep | 0.105 | 0.245 |
| BM25 | 0.024 | 0.055 |
| embedding (exact) | 0.006 | 0.287 |
| repo-map style | 0.546 | 1.875 |
| full (rank only) | 0.642 | 1.997 |
| full + knapsack pack at 8k | 4.277 | 6.888 |
| no graph (rank only) | 0.064 | 0.155 |
| greedy + pack at 8k | 0.863 | 2.272 |

Source: `bench/swebench/results/report.json`, `splits.held_out.query_latency_seconds`. PageRank accounts for most of the ranking time (no-graph is about ten times faster), and the exact knapsack dominates end-to-end latency. Per-task index time, including first-time indexing at each base commit, had p50 11.29 s and p95 38.75 s.

An optional Rust kernel for HNSW distance computation was profiled on 120 vectors of 384 dimensions with 20 queries: pure Python took 18.78 s and native 2.81 s, a 6.69x speedup with identical graphs and query results (`bench/vector/native_profile.json`, [native-experiment.md](native-experiment.md)).

Component micro-benchmarks on synthetic data (seed 81) check speed and correctness, not retrieval quality:

| Component | Setup | Result |
| --- | --- | --- |
| BM25F | 200 symbols, 100 queries | p50 1.07 ms, p95 2.33 ms |
| HNSW (Python) | 400 vectors, 16 dims, M=12, efSearch=100 | recall@10 1.0; build 11.17 s; query p50 17.7 ms, p95 42.5 ms |
| Knapsack vs greedy | 40 groups × 4 options, budgets 256–2,048 | greedy reached 0.976–0.9998 of the DP optimum |

Sources: `bench/lexical/results.json`, `bench/vector/results.json`, `bench/packing/results.json`; `bench/vector/hnsw_reference.json` records the hnswlib reference comparison.

## Agent comparison

A small end-to-end check gave a local model eight injected-bug repair tasks, with and without Smriti context. With qwen2.5-0.5b-instruct (Q4_K_M) at temperature 0, one attempt per task and a 1,500-token context, both conditions solved 0 of 8 and edited no function (`bench/agent/results.json`, [bench/agent/README.md](../bench/agent/README.md)). The model invented new function names instead of editing the named one, so this result says nothing about whether Smriti helps an agent. The harness itself is validated: an oracle agent solves 8/8 and a no-op agent 0/8.

## Findings and what they mean

- **Memory freshness is strongly validated.** Perfect staleness precision and recall over 12,736 observations of real history, exact cascade closure and conservative rename handling are the clearest results in the project. The caveats are scope (one repository) and nature: freshness is structural, so it detects changed code, not changed truth.
- **Long-term memory retrieval is reasonable but lexical.** 0.848 recall@5 overall, with temporal reasoning (0.655) the obvious weak spot.
- **Code retrieval ranking is not yet better than BM25.** On 15 held-out tasks the full fusion-plus-graph pipeline is level with or behind BM25 and exact embeddings at function level, and slightly ahead at file level and deep cutoffs. The graph-removal ablation suggests PageRank expansion dilutes precise lexical and vector hits. The sample is too small for firm conclusions, and two repositories do not represent SWE-bench.
- **Incremental indexing is the main bottleneck.** The Merkle and parser layers are incremental, but resolution and publication are not, so fast incremental updates are not yet achieved even on a 98-file repository.

## Limitations

The full list is in [limitations.md](limitations.md). The most important:

- Resolution is static only; dynamic Python patterns are missed, and languages other than Python have shallower resolution.
- Packing is exact only for independent options; dependencies make it approximate. Token counts depend on the configured tokenizer (`cl100k_base` by default).
- Vector search requires a pinned ONNX model that is not bundled, and pure-Python vector distance is slow without the Rust kernel.
- Freshness is structural, identifier renames orphan anchors, and fact recall is lexical.
- Forget covers `memory.sqlite` only, not backups or exported bundles.
- SWE-bench results cover 16 of 707 tasks; LongMemEval is retrieval-only; CodeMem uses one repository; all timings come from one laptop and one run.

## Reproduction

Commands, dataset downloads, pinned revisions and expected values are in [benchmarks.md](benchmarks.md), with SWE-bench details in [swebench-reproduction.md](swebench-reproduction.md). Raw results are committed under `bench/*/results/`.

## Future work

- Make resolution and snapshot publication incremental per changed file, to bring one-line re-index time well below the current 9.6 s.
- Revisit graph expansion: weight or gate PageRank so it reranks rather than displaces strong lexical and vector hits, tuned on validation only.
- Complete the SWE-bench run on more repositories (retrying seaborn and making the cache rename robust on Windows) so method differences can be tested properly.
- Speed up the exact knapsack, or fall back to greedy where it matches, since packing dominates query latency.
- Add date-aware retrieval for temporal questions and evaluate answer accuracy on LongMemEval.
- Repeat the agent comparison with a model large enough to solve some tasks.
- Extend CodeMem to more repositories and to histories that contain real renames.
