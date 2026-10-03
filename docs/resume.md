# Smriti: resume bullets

Numbers below come from committed result files; each bullet cites its source.

- Built code-anchored memory with freshness tracking that flagged stale facts at 1.00 precision and 1.00 recall (87 true positives, 0 false positives, 0 false negatives) across 12,736 observations, 64 probes, and 200 commits of psf/requests.
  - Source: bench/codemem/results/metrics.json
- Designed anchor relocation so 64 of 64 memory facts stayed fresh after file moves, while all 64 identifier renames were conservatively flagged not-fresh.
  - Source: bench/codemem/results/rename_survival.json
- Implemented cascading forget over a git-like memory history that removed the exact expected closure with no resurrected IDs, checked across 201 history branches with a verifying operation log.
  - Source: bench/codemem/results/metrics.json
- Compressed the authenticated memory operation archive losslessly to 20.9% of its size (379,929 to 79,465 bytes), byte-identical with signatures and provenance preserved after decompression.
  - Source: bench/codemem/results/compression.json
- Reached 0.848 session recall@5 on all 500 LongMemEval-S questions using lexical memory retrieval (retrieval only; answer accuracy not measured).
  - Source: bench/longmemeval/results/longmemeval_s.summary.json
- Wrote an optional Rust/PyO3 kernel for a custom HNSW index that ran 6.7x faster than the pure-Python path (18.78 s to 2.81 s, 120 vectors x 384 dims, 20 queries) with identical graph and query results.
  - Source: bench/vector/native_profile.json
- Evaluated a hybrid code retrieval pipeline (BM25F, HNSW, RRF, personalized PageRank, knapsack packing) on 698 of 707 SWE-bench Lite and Verified tasks. On 516 held-out tasks it beat BM25 on function recall@10 (0.355 vs 0.291, paired 95% CI +0.030 to +0.097) and file recall@10 (0.801 vs 0.711). An ablation showed the graph term lowered recall (0.385 without it).
  - Source: bench/swebench/results/report.json, docs/swebench-failures.md
- Cut evaluation cost on Django-sized repositories with output-identical optimizations: call resolution 326 s to 4 s, and HNSW build 384 s to 55 s through a Rust distance store.
  - Source: git history (commits f296213, bd7477f), docs/report.md
- Indexed psf/requests (98 files, 2,487 symbols) cold in 10.9 s at about 92 MB peak RSS on an Intel i3-5005U (4 logical CPUs); end-to-end one-line-edit re-index p50 9.64 s, p95 10.12 s. Backed by a test suite of 286 test functions.
  - Source: bench/swebench/results/performance.json, docs/performance.md, tests/

## Claims to avoid

- Graph-based ranking gains. On held-out SWE-bench tasks, removing personalized PageRank improved function recall@10 by 0.031 (95% CI +0.009 to +0.056); the graph term currently hurts ranking.
- Beating embedding search. The full pipeline (0.355) is not separable from exact embedding search (0.332) on function recall@10 (95% CI −0.011 to +0.057). The gain over BM25 comes mostly from vectors, and full trails BM25 on 5 of 12 repositories.
- Answer accuracy on LongMemEval. Only session retrieval was evaluated; answer_accuracy is null.
- Production use, users, or deployment at scale.
- Improved agent task success over including the whole repository. With Qwen2.5-Coder-7B, Smriti context solved 8/8 injected bugs against 0/8 with the file list only, but whole-repo context also solved 8/8 because the fixture fits the 1,500-token budget.
- Fast incremental indexing. The re-index is about 9.6 s at p50, close to the 10.9 s cold index, because it includes full resolution and snapshot persistence.
- Rename-proof memory. Identifier renames are flagged not-fresh rather than tracked.

## Project description

Smriti is a local, CPU-only memory and context engine for coding agents, exposed as an MCP server. It indexes repositories incrementally with Merkle hashing and tree-sitter (6 languages), builds a scope-aware call graph, and retrieves context through BM25F, a custom HNSW index, rank fusion, and personalized PageRank, packed to a token budget. Agent memories are anchored to code, tracked for freshness, and kept in a bitemporal history with branches, merges, revert, and cascading forget; it also ships an optional Rust kernel, a VS Code extension, and a Docker image.
