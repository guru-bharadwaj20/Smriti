# Limitations

What Smriti does not do, or does only approximately. Each item links to the
document with details.

## Code understanding

- **Static resolution only.** Monkey-patching, replacing decorators, metaclasses,
  reflection, dependency injection, star imports and computed imports are not
  resolved exactly. Uncertain targets become low-confidence `may_call` edges,
  never claimed calls ([resolution.md](resolution.md)).
- **Uneven language depth.** Python has scope-aware resolution with C3 method
  order. TypeScript and Java extract structure only. Go, C and C++ resolve
  lexical and same-package calls; no macro expansion, template instantiation,
  overload selection or interface dispatch ([languages.md](languages.md)).
- **Cross-language edges are declared, not inferred.** HTTP/gRPC links require
  explicit `ApiBinding` declarations.
- **Native parser pin.** tree-sitter is held below 0.26 because 0.26.0 crashes
  under repeated incremental parsing ([parser-compatibility.md](parser-compatibility.md)).

## Retrieval and packing

- **Packing is approximate under dependencies.** The knapsack is exact only for
  independent symbols; class context for methods may be charged more than once
  ([packing.md](packing.md)).
- **Token counts are tokenizer-specific.** The default is `cl100k_base`; agents
  using another tokenizer must configure it or budgets will be off.
- **Vector search is optional.** Without the pinned ONNX model (not downloaded
  automatically) retrieval is lexical + graph only.
- **Pure-Python vectors are slow.** Distance computation dominates HNSW time; the
  optional Rust kernel gives 6.7x on one benchmark but is not the production path
  ([native-experiment.md](native-experiment.md)).
- **Incremental indexing is not yet incremental end to end.** Only changed files
  are re-parsed, but resolution and snapshot publication cover the whole
  repository: a one-line edit on psf/requests takes 9.6 s (p50) against 10.9 s
  for a cold index ([performance.md](performance.md)).
- **Knapsack packing is slow on this hardware.** Packing an 8k-token context
  takes 4.3 s at p50 after ranking; greedy packing takes 0.9 s and reached the
  same coverage on the measured tasks.
- **Ranking does not beat BM25 yet.** On 15 held-out SWE-bench tasks, function
  recall@10 is 0.267 for the full pipeline against 0.333 for BM25 (interval
  includes zero) ([swebench-failures.md](swebench-failures.md)).

## Memory

- **Freshness is structural.** It detects that anchored code changed, not whether
  a remembered claim is still semantically true. A stale fact may still be
  correct; a fresh fact may have been wrong from the start.
- **Identifier renames orphan anchors.** Only identical-content moves are
  followed; renaming a function changes its hashed body (64/64 renames were
  flagged in the controlled experiment).
- **Recall is lexical.** Fact search is BM25 over text; there is no semantic fact
  extraction or summarization. LongMemEval temporal-reasoning recall@5 is 0.655.
- **Sync authenticates groups, not people.** HMAC bundles prove possession of a
  shared key, not individual authorship ([memory.md](memory.md)).
- **Forgetting covers `memory.sqlite` only.** Backups, exported bundles and
  agent transcripts are outside Smriti's control.

## Evaluation

- **SWE-bench numbers come from a small subset.** 16 of 707 unique tasks were
  measured (psf/requests 12, pallets/flask 4); all 6 seaborn tasks failed at
  clone while the network was down. The full run needs days of CPU time on the
  reference laptop.
- **LongMemEval is retrieval-only.** No answers are generated; numbers are not
  comparable to the answer-accuracy leaderboard ([longmemeval.md](longmemeval.md)).
- **CodeMem uses one repository.** 200 Requests commits; a single project's
  editing style may not generalize.
- **Single machine, single run.** Timings come from one Intel i3-5005U laptop,
  sometimes with other workloads running; they are not distributions.

## Scope

No hosted service, authentication or multi-user server. The UI binds to
localhost only. The VS Code extension (`vscode/`) is unpublished and depends on
the `smriti` CLI being installed.
