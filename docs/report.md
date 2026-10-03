# Smriti project report

## Summary

Smriti is a local, CPU-only memory and context engine for coding agents, exposed over MCP. It indexes a repository incrementally, parses six languages with tree-sitter, builds a scope-aware call graph, retrieves code with lexical, vector and graph signals, packs the result into a strict token budget, and keeps a code-anchored memory whose facts are marked fresh, stale or orphaned as the code changes. Replayed over 200 real psf/requests commits with 64 probe facts, the memory layer detected staleness with precision and recall of 1.0 across 12,736 observations, and cascading forget removed exactly the expected closure of facts with no resurrection across 201 history branches. On LongMemEval-S (retrieval only, no answer generation), session recall@5 was 0.848 over 500 questions. On 516 held-out SWE-bench tasks (698 of 707 Lite and Verified tasks measured, all 12 repositories), the full retrieval pipeline beats BM25 on function recall@10 (0.355 vs 0.291; paired 95% interval for the difference 0.030 to 0.097). It does not separate from exact embedding search, and removing the graph term scores higher still (0.385). A one-line edit still costs about 9.6 s to re-index on requests because resolution and snapshot publication are whole-repository. In short: the memory freshness design holds up well under test, the ranking stack beats BM25 mainly through embeddings while the PageRank term currently costs recall, and incremental indexing is the main performance gap.

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

The target was 707 unique evaluations (800 dataset rows across Lite and Verified), across all 12 repositories. 698 were measured (790 dataset rows). The other 9 were excluded before scoring by the leakage guard, because their issue text already contains lines of the gold patch (django 5, sympy 2, matplotlib 1, scikit-learn 1). No task failed for tooling reasons. Failures are recorded, never scored as zero ([swebench-failures.md](swebench-failures.md)). Retrieval input is the problem statement; gold functions and files come from the patch. Splits follow `sha256(instance_id)` modulo 5: 152 validation tasks and 546 held-out tasks, 516 of which have at least one gold function. The graph weight was tuned on 34 validation tasks only (`bench/swebench/results/tuning.summary.json`); held-out tasks were never used for tuning. Django supplies 211 of the 516 held-out tasks, so it dominates the means.

Held-out split, 516 tasks with function gold:

| Method | Fn R@1 | Fn R@5 | Fn R@10 | Fn R@20 | Fn R@50 | File R@1 | File R@5 | File R@10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| grep | 0.000 | 0.000 | 0.000 | 0.000 | 0.006 | 0.012 | 0.115 | 0.209 |
| BM25 | 0.116 | 0.227 | 0.291 | 0.361 | 0.457 | 0.336 | 0.608 | 0.711 |
| embedding (exact) | 0.108 | 0.245 | 0.332 | 0.399 | 0.508 | 0.273 | 0.600 | 0.703 |
| repo-map style | 0.002 | 0.004 | 0.011 | 0.013 | 0.036 | 0.024 | 0.082 | 0.152 |
| Smriti full | 0.100 | 0.286 | 0.355 | 0.487 | 0.579 | 0.351 | 0.702 | 0.801 |
| full, no vector | 0.050 | 0.196 | 0.273 | 0.362 | 0.457 | 0.300 | 0.622 | 0.715 |
| full, no graph | 0.124 | 0.305 | 0.385 | 0.487 | 0.562 | 0.357 | 0.682 | 0.784 |
| full, greedy packing | 0.100 | 0.286 | 0.355 | 0.487 | 0.579 | 0.351 | 0.702 | 0.801 |

Source: `bench/swebench/results/report.json`, `splits.held_out.methods`.

Packed-budget coverage is the mean fraction of gold functions included in the packed context (held-out, 516 tasks).

| Method | 4k tokens | 8k tokens | 16k tokens |
| --- | --- | --- | --- |
| full | 0.447 | 0.546 | 0.590 |
| no vector | 0.376 | 0.423 | 0.464 |
| no graph | 0.437 | 0.526 | 0.585 |
| greedy | 0.452 | 0.543 | 0.592 |

Source: `bench/swebench/results/report.json`, `splits.held_out.methods.*.budget_coverage`.

| Paired bootstrap, function recall@10 (2,000 samples, seed 0) | Mean difference | 95% interval |
| --- | --- | --- |
| full minus BM25 | +0.063 | [+0.030, +0.097] |
| full minus exact embedding | +0.023 | [−0.011, +0.057] |
| no graph minus full | +0.031 | [+0.009, +0.056] |

Source: `bench/swebench/results/report.json`, `paired_full_minus_*`; the no-graph row was computed with the same bootstrap from `bench/swebench/results/raw.jsonl`.

On the full run, the full pipeline beats BM25 on function recall@10 (0.355 vs 0.291), and the interval excludes zero. It also leads on file recall@10 (0.801 vs 0.711) and function recall@50 (0.579 vs 0.457). It is not separable from exact embedding search at function recall@10. The gain is uneven by repository: full is behind BM25 on astropy, requests, seaborn, pylint and pytest (see [swebench-failures.md](swebench-failures.md)).

The ablations give two clear results. Vectors carry most of the gain: removing them drops function recall@10 to 0.273 and 8k coverage from 0.546 to 0.423. The graph, as configured, hurts ranking: removing personalized PageRank raises function recall@10 from 0.355 to 0.385, an interval that excludes zero. That held-out ablation contradicts the validation tuning, which chose graph weight 1.0 on only 34 tasks, with 1.0 at the edge of the grid. On packed context the graph helps a little (8k coverage 0.546 vs 0.526). Exact knapsack and greedy packing give the same ranking and coverage within 0.005.

## Performance

| Measurement | Value |
| --- | --- |
| Cold index, requests (98 files, 2,487 symbols) | 10.86 s |
| Sampled peak RSS during cold index | 91.8 MB |
| One-line edit re-index, p50 (20 runs) | 9.64 s |
| One-line edit re-index, p95 | 10.12 s |

Source: `bench/swebench/results/performance.json`, [performance.md](performance.md). Each incremental run changes exactly one file and only that file is reparsed, but resolution and snapshot publication still process the whole repository, so an incremental update costs about 90% of a cold index.

Query latency on the 546 held-out tasks. The full run executed about 40 runner processes at once on one machine, so these timings include heavy CPU contention. They are indicative only and are not comparable with the single-process numbers above.

| Method | p50 (s) | p95 (s) |
| --- | --- | --- |
| grep | 1.66 | 5.23 |
| BM25 | 0.35 | 0.87 |
| embedding (exact) | 0.19 | 0.60 |
| repo-map style | 23.77 | 40.87 |
| full (rank only) | 44.74 | 76.01 |
| full + knapsack pack at 8k | 5.00 | 7.43 |
| no graph (rank only) | 0.65 | 1.35 |
| greedy + pack at 8k | 0.28 | 0.63 |

Source: `bench/swebench/results/report.json`, `splits.held_out.query_latency_seconds`. On repositories of this size (Django has about 33,000 symbols and 350,000 edges), personalized PageRank dominates ranking time; the no-graph variant is about 70 times faster. Per-task index time, including first-time indexing at each base commit, had p50 78 s and p95 168 s.

Run conditions. The run used Windows with `core.autocrlf=true`, so checkouts have CRLF line endings, which changes symbol text and token counts. Embeddings for each repository's base commits were computed ahead of time into the same cache the runner reads, using a multithreaded encoder. Cached vectors can differ from single-threaded ones at float-rounding level. To finish in a day, several performance fixes went into the resolver, the HNSW build (through the Rust kernel) and retrieval memoization. Each was checked to give identical edges, graphs or rankings on Django before use (commits `f296213`, `bd7477f`, `c205275`). Two crash fixes made non-UTF-8 sources and unnamed C++ template definitions parse (`59aecd3`, `4313e0f`). All results share one configuration ID, `691031a0…5b21`.

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
- **Code retrieval beats BM25, but the graph hurts.** On 516 held-out SWE-bench tasks from 12 repositories, the full pipeline improves function recall@10 over BM25 by 0.063 (95% interval 0.030 to 0.097). Almost all of that comes from embeddings: full is not separable from exact embedding search. Removing personalized PageRank improves recall@10 by a further 0.031 (interval 0.009 to 0.056) and makes ranking about 70 times faster. The graph weight chosen on 34 validation tasks does not hold up on the held-out set.
- **Incremental indexing is the main bottleneck.** The Merkle and parser layers are incremental, but resolution and publication are not, so fast incremental updates are not yet achieved even on a 98-file repository.

## Limitations

The full list is in [limitations.md](limitations.md). The most important:

- Resolution is static only; dynamic Python patterns are missed, and languages other than Python have shallower resolution.
- Packing is exact only for independent options; dependencies make it approximate. Token counts depend on the configured tokenizer (`cl100k_base` by default).
- Vector search requires a pinned ONNX model that is not bundled, and pure-Python vector distance is slow without the Rust kernel.
- Freshness is structural, identifier renames orphan anchors, and fact recall is lexical.
- Forget covers `memory.sqlite` only, not backups or exported bundles.
- SWE-bench results cover 698 of 707 tasks from one run on one machine; LongMemEval is retrieval-only; CodeMem uses one repository; all timings come from one laptop and one run.

## Reproduction

Commands, dataset downloads, pinned revisions and expected values are in [benchmarks.md](benchmarks.md), with SWE-bench details in [swebench-reproduction.md](swebench-reproduction.md). Raw results are committed under `bench/*/results/`.

## Future work

- Make resolution and snapshot publication incremental per changed file, to bring one-line re-index time well below the current 9.6 s.
- Revisit graph expansion: the held-out ablation shows PageRank lowering function recall@10. Weight or gate it so it reranks rather than displaces strong lexical and vector hits, tuned on validation only.
- Retune or remove the graph term on the 152-task validation split, and make the retrieval cache rename robust to transient Windows `PermissionError`s.
- Speed up the exact knapsack, or fall back to greedy where it matches, since packing dominates query latency.
- Add date-aware retrieval for temporal questions and evaluate answer accuracy on LongMemEval.
- Repeat the agent comparison with a model large enough to solve some tasks.
- Extend CodeMem to more repositories and to histories that contain real renames.
