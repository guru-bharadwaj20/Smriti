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
- Evaluated a hybrid retrieval pipeline (BM25F, HNSW, RRF, personalized PageRank, knapsack packing) on 15 held-out SWE-bench tasks: file recall@10 of 0.933 vs 0.867 for BM25; function recall@10 of 0.267, below BM25's 0.333.
  - Source: bench/swebench/results/report.json, docs/swebench-failures.md
- Indexed psf/requests (98 files, 2,487 symbols) cold in 10.9 s at about 92 MB peak RSS on an Intel i3-5005U (4 logical CPUs); end-to-end one-line-edit re-index p50 9.64 s, p95 10.12 s. Backed by a test suite of 286 test functions.
  - Source: bench/swebench/results/performance.json, docs/performance.md, tests/

## Claims to avoid

- SWE-bench-wide results. Only 16 of 707 target evaluations were measured (15 held-out instances scored); 691 remain.
- Beating BM25 or other baselines on function-level retrieval. The full pipeline scored 0.267 function recall@10 vs 0.333 for BM25 and exact embeddings. Ablations without the vector or graph components scored the same 0.267 on function recall@10. The only measured component effect is on packed context: removing vectors lowered 8k-token coverage from 0.567 to 0.400, while removing the graph raised it to 0.633 (15 tasks).
- Answer accuracy on LongMemEval. Only session retrieval was evaluated; answer_accuracy is null.
- Production use, users, or deployment at scale.
- Improved agent task success or fewer agent tokens. The one agent comparison run (Qwen2.5-0.5B, 8 tasks) solved 0/8 with and without Smriti and is uninformative.
- Fast incremental indexing. The re-index is about 9.6 s at p50, close to the 10.9 s cold index, because it includes full resolution and snapshot persistence.
- Rename-proof memory. Identifier renames are flagged not-fresh rather than tracked.

## Project description

Smriti is a local, CPU-only memory and context engine for coding agents, exposed as an MCP server. It indexes repositories incrementally with Merkle hashing and tree-sitter (6 languages), builds a scope-aware call graph, and retrieves context through BM25F, a custom HNSW index, rank fusion, and personalized PageRank, packed to a token budget. Agent memories are anchored to code, tracked for freshness, and kept in a bitemporal history with branches, merges, revert, and cascading forget; it also ships an optional Rust kernel, a VS Code extension, and a Docker image.
