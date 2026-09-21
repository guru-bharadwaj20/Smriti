# Design decisions

## P01.01: Language scope

The initial supported language is Python 3.12+. Python symbol extraction uses
tree-sitter and name resolution is deliberately static: dynamic dispatch produces
uncertain candidate edges rather than a claim of runtime certainty. TypeScript
and Java extraction follow with language-specific fixtures. Go and C/C++ are
optional extensions; their absence must remain visible in the checklist.

Core operation is local and CPU-only. Embeddings and local model summaries are
optional capabilities with explicit model configuration; no paid API is required.

## P01.02: Architecture boundaries

The watcher emits changed paths. The Merkle layer identifies unchanged subtrees
and file moves. Parsing extracts symbols, imports, and candidate calls. Resolution
produces weighted graph edges. Lexical and vector indexes generate candidate
lists; reciprocal rank fusion and personalized PageRank expand and rank them.
The packer renders selected symbol representations within a strict token budget.

Memory is a separate SQLite-backed operation log with code anchors. Index changes
trigger freshness events; branch-aware views expose facts to retrieval. The service
owns immutable query snapshots and transaction boundaries. CLI, MCP, and the local
UI call the same service rather than duplicating retrieval or memory rules.

Storage is local to each repository, under `.smriti/`. Benchmark ground truth,
patches, model weights, and evaluation checkouts live outside indexed source.
Deterministic ranking and reproducible replay take precedence over optional UI,
summarization, and Rust optimization.
