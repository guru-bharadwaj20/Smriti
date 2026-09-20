# Contributing to Smriti

Smriti is a planned local, CPU-first memory and context engine for coding agents, exposed through MCP. Its central feature is code-anchored memory with freshness tracking, bitemporal history, branches, merges, rollback, and cascading deletion. Retrieval combines incremental indexing, a symbol graph, BM25F, a custom HNSW index, personalised PageRank, and token-budgeted context packing.

This checklist translates the project proposal into individually trackable work. It describes planned work, not existing functionality. The proposal and linked articles are design inputs; this document records the project's contribution workflow.

## Mandatory workflow

**Commit every minor, coherent change.** Do not accumulate unrelated edits into one commit. This applies to code, documentation, configuration, fixes, and task-status updates.

1. Choose a pending task by its stable ID; split it further if it contains independently reviewable changes.
2. Inspect related code and agree on the expected behavior before editing.
3. Make one small change and run the checks appropriate to that change.
4. Change its status to ✅ Done only when its deliverable and relevant checks are complete. Add a file, test, report, or commit reference in Evidence. Keep unfinished work ❌ Pending and describe any blocker there.
5. Commit the implementation and its checklist update together. Use messages such as `feat(memory): P09.04 track anchor hashes` or `docs: P00.02 introduce project idea`.
6. Review the staged diff and repository status before starting the next minor change. Stage only files belonging to that change; do not commit unrelated work or generated indexes, model weights, credentials, or benchmark checkouts.

Use the requested repository-local identity for this project:

```powershell
git config --local user.name "guru-bharadwaj20"
git config --local user.email "gururb20@gmail.com"
git diff --check
git diff --cached
git commit -m "docs: describe the completed minor change"
git status --short
```

Never rewrite shared commit history merely to update a checklist. Contributors and coding agents must follow the minor-change commit rule throughout the project.

## Status and completion rules

| Indicator | Meaning | When to use it |
| --- | --- | --- |
| ❌ Pending | Incomplete, in progress, or blocked | Default for every unimplemented subtask |
| ✅ Done | Deliverable exists and relevant verification passed | Record completion evidence in the same commit |

Keep task IDs stable when adding or reordering work. A phase is complete only when all required rows are done. Optional work is explicitly separated and does not block the core release. Performance values are targets until measured; publish actual results with hardware, dataset versions, seeds, and configuration. Do not claim complete language resolution for dynamic code, optimal packing under unhandled constraints, or standard LongMemEval answer accuracy from retrieval-only experiments.

## Team and schedule

The 16-week schedule is an estimate for four people. A, B, C, and D are roles to assign, not contributor names. Parallel work must respect the dependencies below; scope reductions should be documented before implementation.

| Window | A: indexing and resolution | B: lexical and vector search | C: parsing and memory | D: infrastructure and evaluation |
| --- | --- | --- | --- | --- |
| Weeks 1–2 | Study indexing and retrieval baselines | Study BM25F and HNSW | Study temporal memory and parsing | Set up repository, CI, evaluation fixtures |
| Weeks 3–5 | Merkle tree and watcher | Tokenizer and BM25F | Symbol extraction | Retrieval harness and baselines |
| Weeks 6–8 | Scope and call resolution | CPU embeddings and HNSW | Anchors and freshness | Fusion and PageRank |
| Weeks 9–10 | Rename tracking and crash safety | Vector deletion and oracle comparisons | Bitemporal facts and operation log | Context packing |
| Weeks 11–12 | MCP and snapshots | Retrieval integration and tuning | Branches, merges, cascading deletion | Commit-replay benchmark |
| Weeks 13–14 | SWE-bench runs with team | Ablations and performance with team | LongMemEval with team | Consolidate reproducible results |
| Weeks 15–16 | Release and documentation with team | Demo and profiling with team | Memory demo and documentation with team | UI, reports, release checklist |

## Phase checklist

Each table tracks one minor deliverable per row. Evidence stays `—` until there is a concrete implementation, check, report, or documented decision to reference.

