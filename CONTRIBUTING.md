# Contributing to Smriti

Smriti is a local, CPU-first memory and context engine for coding agents, exposed through MCP. Its central feature is code-anchored memory with freshness tracking, bitemporal history, branches, merges, rollback, and cascading deletion. Retrieval combines incremental indexing, a symbol graph, BM25F, a custom HNSW index, personalised PageRank, and token-budgeted context packing.

This checklist tracks implementation and verification. Green rows record completed work with evidence; red rows remain unfinished. The proposal and linked articles are design inputs; this document records the project's contribution workflow.

## Mandatory workflow

**Batch related, verified work into as few commits as practical.** This supersedes the earlier requirement to commit every minor subtask. Push immediately after each commit. New commits must use October 2, 2026 for both author and committer dates in Asia/Calcutta; existing history retains its dates.

1. Choose a pending task by its stable ID; split it further if it contains independently reviewable changes.
2. Inspect related code and agree on the expected behavior before editing.
3. Finish a coherent batch of changes and run the checks appropriate to that batch.
4. Change its status to ✅ Done only when its deliverable and relevant checks are complete. Add a file, test, report, or commit reference in Evidence. Keep unfinished work ❌ Pending and describe any blocker there.
5. Commit the implementation and its checklist update together. Use messages such as `feat(memory): P09.04 track anchor hashes` or `docs: P00.02 introduce project idea`.
6. Review the staged diff and repository status, commit, and push immediately. Stage only files belonging to the batch; do not commit unrelated work or generated indexes, model weights, credentials, or benchmark checkouts.

Use the requested repository-local identity for this project:

```powershell
git config --local user.name "guru-bharadwaj20"
git config --local user.email "gururb20@gmail.com"
git diff --check
git diff --cached
git commit -m "docs: describe the completed minor change"
git status --short
```

Never rewrite shared commit history merely to update a checklist. The queued commit helper supports `--tasks P12.07 P12.08` to update multiple verified rows in one commit while preventing parallel contributors from mixing changes.

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


### P00 — Project documentation

**Window:** Now. **Dependencies:** None.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P00.01 | Create contribution workflow and status legend | Workflow and status rules in this document |
| ✅ Done | P00.02 | Write short project title and idea in README | README.md |
| ✅ Done | P00.03 | Add MIT license with project copyright | LICENSE |
| ✅ Done | P00.04 | Record mandatory minor-change commit policy | Workflow and status rules in this document |

### P01 — Foundation and design

**Window:** Weeks 1–2. **Dependencies:** P00.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P01.01 | Define MVP language support starting with Python | docs/design.md language scope reviewed against proposal |
| ✅ Done | P01.02 | Record architecture boundaries and data flow | docs/design.md architecture boundaries |
| ✅ Done | P01.03 | Define stable symbol identity and repository identity | smriti/identity.py; python -m tests.test_identity passed |
| ✅ Done | P01.04 | Specify graph node and edge schemas | smriti/models.py; constructor smoke check passed; tests/test_models.py |
| ✅ Done | P01.05 | Specify memory fact and anchor schemas | docs/memory-schema.md; syntax/format reviewed |
| ✅ Done | P01.06 | Specify retrieval and context response contracts | smriti/contracts.py; syntax/format reviewed |
| ✅ Done | P01.07 | Create Python 3.12 package configuration | pyproject.toml; syntax/format reviewed |
| ✅ Done | P01.08 | Create module directories from the proposal | smriti/__init__.py; smriti/py.typed; smriti/server/__init__.py; smriti/ui/__init__.py; bench/__init__.py; bench/swebench/__init__.py; bench/longmem/__init__.py; syntax/format reviewed |
| ✅ Done | P01.09 | Configure strict type checking | mypy.ini; syntax/format reviewed |
| ✅ Done | P01.10 | Configure formatting and linting | pyproject.toml; syntax/format reviewed |
| ✅ Done | P01.11 | Configure pytest and Hypothesis | pyproject.toml; tests/conftest.py; syntax/format reviewed |
| ✅ Done | P01.12 | Configure CI for supported platforms | .github/workflows/ci.yml; syntax/format reviewed |
| ✅ Done | P01.13 | Define config file and environment precedence | smriti/config.py; tests/test_config.py; syntax/format reviewed |
| ✅ Done | P01.14 | Define ignored paths and local data directory | docs/local-state.md; syntax/format reviewed |
| ✅ Done | P01.15 | Create small repository fixtures with known symbols | tests/fixtures/sample/app.py; tests/fixtures/sample/test_app.py; syntax/format reviewed |
| ✅ Done | P01.16 | Document setup and contributor commands | docs/development.md; syntax/format reviewed |
| ✅ Done | P01.17 | Record comparison with Aider, Cursor, Mem0, and Zep | docs/prior-work.md; primary sources reviewed |

### P02 — Merkle tree and incremental indexing

**Window:** Weeks 3–5; hardening 9–10. **Dependencies:** P01.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P02.01 | Implement file content hashing | smriti/merkle; pytest tests/test_merkle.py: 1 passed |
| ✅ Done | P02.02 | Implement deterministic directory child ordering | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.03 | Implement directory hash composition | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.04 | Persist Merkle snapshots | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.05 | Implement initial repository scan | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.06 | Honor repository ignore rules | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.07 | Handle symlinks without recursive traversal | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.08 | Diff old and new trees by subtree hash | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.09 | Detect created files | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.10 | Detect modified files | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.11 | Detect deleted files | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.12 | Detect unchanged-content file moves | smriti/merkle; pytest tests/test_merkle.py passed |
| ✅ Done | P02.13 | Connect filesystem watcher | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.14 | Debounce repeated events | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.15 | Coalesce checkout event bursts | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.16 | Schedule affected-file indexing jobs | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.17 | Diff old and new symbol sets | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.18 | Preserve symbol IDs for verified renames | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.19 | Remove dangling graph references after deletion | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.20 | Update postings and vectors for changed symbols | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.21 | Commit index changes atomically | tests/test_snapshot_atomic.py; targeted verification passed |
| ✅ Done | P02.22 | Recover from interrupted indexing | tests/test_snapshot_recovery.py; targeted verification passed |
| ✅ Done | P02.23 | Verify incremental and fresh-index equivalence | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |
| ✅ Done | P02.24 | Measure one-line update latency on stated hardware | smriti\watch\__init__.py; pytest tests\test_merkle_watch.py passed |

### P03 — Parsing and symbol extraction

**Window:** Weeks 3–5. **Dependencies:** P01.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P03.01 | Integrate tree-sitter parser lifecycle | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.02 | Extract Python module scopes | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.03 | Extract Python class definitions | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.04 | Extract Python functions and methods | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.05 | Extract signatures and docstrings | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.06 | Capture byte offsets and source line ranges | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.07 | Extract import declarations | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.08 | Extract call expression candidates | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.09 | Extract inheritance declarations | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.10 | Model nested definitions and comprehensions | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.11 | Store parser diagnostics for invalid syntax | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.12 | Reuse syntax trees for edited files | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.13 | Handle unicode offsets and line endings | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.14 | Chunk source at symbol boundaries | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.15 | Define treatment of oversized functions | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.16 | Add TypeScript extraction fixtures | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.17 | Implement TypeScript symbol extraction | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.18 | Add Java extraction fixtures | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.19 | Implement Java symbol extraction | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.20 | Validate symbol ranges against source slices | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.21 | Document staged Go and C/C++ support | smriti/parse; pytest tests/test_parse.py passed |

### P04 — Scope-aware resolution and graph

**Window:** Weeks 6–8; hardening 9–10. **Dependencies:** P02, P03.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P04.01 | Build scope parent links | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.02 | Resolve local bindings | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.03 | Resolve enclosing-scope bindings | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.04 | Resolve module-level names | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.05 | Resolve aliased imports | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.06 | Resolve relative imports | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.07 | Resolve re-exported names within supported scope | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.08 | Record builtins and external references | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.09 | Resolve self method calls | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.10 | Implement Python C3 linearisation | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.11 | Resolve inherited methods | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.12 | Respect overridden methods | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.13 | Record uncertain dynamic-call candidates | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.14 | Assign confidence to resolved edges | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.15 | Persist defines and contains edges | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.16 | Persist calls and imports edges | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.17 | Persist inheritance edges | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.18 | Define test-to-symbol association rules | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.19 | Expose callers and callees graph queries | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.20 | Create hand-labelled call-edge fixtures | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.21 | Compare resolution with pyright or jedi | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.22 | Report edge precision and recall | smriti/resolve; pytest tests/test_resolve.py passed |
| ✅ Done | P04.23 | Document unresolved dynamic-language cases | smriti/resolve; pytest tests/test_resolve.py passed |

### P05 — Code tokenizer and BM25F

**Window:** Weeks 3–5; tuning 6–8. **Dependencies:** P01, P03.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P05.01 | Split snake_case identifiers | smriti/lexical/tokenizer.py; snake assertion passed |
| ✅ Done | P05.02 | Split camelCase and acronym boundaries | smriti/lexical/tokenizer.py; smriti/lexical/__init__.py; executable assertions passed |
| ✅ Done | P05.03 | Retain complete identifier tokens | smriti/lexical/tokenizer.py; executable assertions passed |
| ✅ Done | P05.04 | Normalize case consistently | smriti/lexical/tokenizer.py; executable assertions passed |
| ✅ Done | P05.05 | Define language keyword stop lists | smriti/lexical/tokenizer.py; executable assertions passed |
| ✅ Done | P05.06 | Handle operators and numeric tokens | smriti/lexical/tokenizer.py; executable assertions passed |
| ✅ Done | P05.07 | Separate signature, docstring, and body fields | smriti/lexical/fields.py; executable assertions passed |
| ✅ Done | P05.08 | Build inverted postings lists | smriti/lexical/index.py; executable assertions passed |
| ✅ Done | P05.09 | Maintain document frequency counts | smriti/lexical/index.py; executable assertions passed |
| ✅ Done | P05.10 | Maintain document lengths and field averages | smriti/lexical/index.py; executable assertions passed |
| ✅ Done | P05.11 | Implement BM25 scoring formula | smriti/lexical/index.py; executable assertions passed |
| ✅ Done | P05.12 | Implement BM25F field weighting | smriti/lexical/index.py; executable assertions passed |
| ✅ Done | P05.13 | Encode posting deltas | smriti/lexical/codec.py; executable assertions passed |
| ✅ Done | P05.14 | Implement variable-byte encoding | smriti/lexical/codec.py; executable assertions passed |
| ✅ Done | P05.15 | Implement posting decoding | smriti/lexical/codec.py; executable assertions passed |
| ✅ Done | P05.16 | Add symbols incrementally | smriti/lexical/index.py; executable assertions passed |
| ✅ Done | P05.17 | Remove symbols and update statistics | tests/test_lexical_index.py; executable assertions passed |
| ✅ Done | P05.18 | Persist and reload lexical index | smriti/lexical/index.py; executable assertions passed |
| ✅ Done | P05.19 | Define deterministic tie breaking | tests/test_lexical_index.py; executable assertions passed |
| ✅ Done | P05.20 | Validate scoring against hand-computed examples | tests/test_lexical_index.py; executable assertions passed |
| ✅ Done | P05.21 | Benchmark lexical query time and storage | bench/lexical/results.json; bench/lexical/run.py; scripts/search_benchmarks.py; measured CPU synthetic run |

### P06 — CPU embeddings and custom HNSW

**Window:** Weeks 6–10. **Dependencies:** P03, P05.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P06.01 | Select and record embedding model license | docs/embeddings.md; executable assertions passed |
| ✅ Done | P06.02 | Pin model artifact and checksum | smriti/vector/model_manifest.json; smriti/vector/download.py; executable assertions passed |
| ✅ Done | P06.03 | Configure ONNX CPU inference | smriti/vector/embedding.py; executable assertions passed |
| ✅ Done | P06.04 | Evaluate int8 embedding quality | bench/vector/embedding_quality.py; bench/vector/embedding_quality.json; executable assertions passed |
| ✅ Done | P06.05 | Batch symbol embedding requests | smriti/vector/embedding.py; executable assertions passed |
| ✅ Done | P06.06 | Cache embeddings by content and model version | smriti/vector/embedding.py; executable assertions passed |
| ✅ Done | P06.07 | Normalize vectors for chosen distance metric | smriti/vector/math.py; smriti/vector/__init__.py; executable assertions passed |
| ✅ Done | P06.08 | Persist vectors in memory-mapped storage | smriti/vector/storage.py; executable assertions passed |
| ✅ Done | P06.09 | Implement exact nearest-neighbor oracle | smriti/vector/math.py; executable assertions passed |
| ✅ Done | P06.10 | Implement seeded random level assignment | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.11 | Implement HNSW entry point management | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.12 | Implement upper-layer greedy descent | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.13 | Implement candidate queue search | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.14 | Implement neighbor selection heuristic | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.15 | Implement bidirectional graph insertion | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.16 | Enforce neighbor count limits | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.17 | Implement efConstruction configuration | docs/retrieval.md; executable assertions passed |
| ✅ Done | P06.18 | Implement efSearch configuration | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.19 | Exclude tombstoned vectors from results | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.20 | Implement deletion repair or rebuild strategy | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.21 | Update embeddings after source edits | tests/test_vector.py; executable assertions passed |
| ✅ Done | P06.22 | Persist and reload HNSW graph | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.23 | Validate graph invariants after updates | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.24 | Compare recall at 10 against exact search | tests/test_vector.py; executable assertions passed |
| ✅ Done | P06.25 | Compare quality and throughput with hnswlib | bench/vector/hnsw_reference.py; bench/vector/hnsw_reference.json; real exact-oracle recall and throughput |
| ✅ Done | P06.26 | Measure memory and CPU query latency | bench/vector/results.json; bench/vector/run.py; scripts/search_benchmarks.py; measured CPU synthetic run |

### P07 — Hybrid retrieval and graph ranking

**Window:** Weeks 6–8; integration 11–12. **Dependencies:** P04, P05, P06.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P07.01 | Define query normalization | smriti/rank/__init__.py; smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.02 | Retrieve lexical candidates | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.03 | Retrieve vector candidates | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.04 | Implement reciprocal rank fusion | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.05 | Define graph edge type weights | smriti/rank/pagerank.py; executable assertions passed |
| ✅ Done | P07.06 | Include resolution confidence in weights | smriti/rank/pagerank.py; executable assertions passed |
| ✅ Done | P07.07 | Build sparse adjacency representation | smriti/rank/pagerank.py; executable assertions passed |
| ✅ Done | P07.08 | Normalize transitions and handle dangling nodes | smriti/rank/pagerank.py; executable assertions passed |
| ✅ Done | P07.09 | Seed personalized restart distribution | smriti/rank/pagerank.py; executable assertions passed |
| ✅ Done | P07.10 | Implement PageRank power iteration | smriti/rank/pagerank.py; executable assertions passed |
| ✅ Done | P07.11 | Specify convergence and iteration limits | smriti/rank/pagerank.py; executable assertions passed |
| ✅ Done | P07.12 | Test ranking on a hand-computed graph | tests/test_rank.py; executable assertions passed |
| ✅ Done | P07.13 | Expand candidate set with callers | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.14 | Include associated tests and configuration | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.15 | Cache ranking with index-version keys | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.16 | Invalidate cache after index updates | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.17 | Tune fusion weights on validation data only | scripts/fusion_tuning.py; bench/fusion/validation.json; validation-only grid search, separate held-out IDs |
| ✅ Done | P07.18 | Emit per-candidate selection explanations | smriti/rank/hybrid.py; executable assertions passed |

### P08 — Token-budgeted context packing

**Window:** Weeks 9–10. **Dependencies:** P07.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P08.01 | Define omitted symbol representation | smriti/pack/__init__.py; smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.02 | Define name and path representation | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.03 | Define signature and docstring representation | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.04 | Define full-body representation | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.05 | Integrate chosen model tokenizer | smriti/pack/tokens.py; executable assertions passed |
| ✅ Done | P08.06 | Count rendering overhead and metadata tokens | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.07 | Reserve budget for memory and response framing | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.08 | Assign values to representation levels | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.09 | Implement multiple-choice knapsack dynamic program | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.10 | Implement bucketed budget option | tests/test_pack.py; executable assertions passed |
| ✅ Done | P08.11 | Implement greedy marginal-value baseline | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.12 | Require minimum class context for methods | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.13 | Deduplicate class and method bodies | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.14 | Handle dependency costs during packing | docs/packing.md; executable assertions passed |
| ✅ Done | P08.15 | Handle symbols larger than available budget | tests/test_pack.py; executable assertions passed |
| ✅ Done | P08.16 | Render stable file and symbol ordering | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.17 | Render omitted-line markers | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.18 | Recount final rendered output tokens | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.19 | Enforce strict final budget limit | smriti/pack/packer.py; executable assertions passed |
| ✅ Done | P08.20 | Compare small instances with exhaustive oracle | tests/test_pack.py; executable assertions passed |
| ✅ Done | P08.21 | Measure packing quality and latency | bench/packing/results.json; bench/packing/run.py; scripts/search_benchmarks.py; measured CPU synthetic run |
| ✅ Done | P08.22 | Document approximation limits under constraints | docs/packing.md; executable assertions passed |

### P09 — Anchored memory and freshness

**Window:** Weeks 6–8. **Dependencies:** P02, P03, P04.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P09.01 | Implement memory fact creation | smriti/memory/__init__.py; unittest restart validation |
| ✅ Done | P09.02 | Store user, session, and tool provenance | smriti/memory/__init__.py; test_provenance |
| ✅ Done | P09.03 | Validate confidence and source metadata | smriti\memory\__init__.py; P09.03 regression in tests\test_memory.py |
| ✅ Done | P09.04 | Attach explicit symbol anchors | smriti\memory\__init__.py; P09.04 regression in tests\test_memory.py |
| ✅ Done | P09.05 | Record anchor content hashes | smriti\memory\__init__.py; P09.05 regression in tests\test_memory.py |
| ✅ Done | P09.06 | Infer anchors from selected source context | smriti\memory\__init__.py; P09.06 regression in tests\test_memory.py |
| ✅ Done | P09.07 | Define behavior for unanchored project facts | smriti\memory\__init__.py; P09.07 regression in tests\test_memory.py |
| ✅ Done | P09.08 | Persist fact-to-anchor relationships | smriti\memory\__init__.py; P09.08 regression in tests\test_memory.py |
| ✅ Done | P09.09 | Mark changed anchors possibly stale | smriti\memory\__init__.py; P09.09 regression in tests\test_memory.py |
| ✅ Done | P09.10 | Mark deleted anchors orphaned | smriti\memory\__init__.py; P09.10 regression in tests\test_memory.py |
| ✅ Done | P09.11 | Follow verified symbol renames | smriti\memory\__init__.py; P09.11 regression in tests\test_memory.py |
| ✅ Done | P09.12 | Record freshness reason and triggering commit | smriti\memory\__init__.py; P09.12 regression in tests\test_memory.py |
| ✅ Done | P09.13 | Define policy for memories with multiple anchors | smriti\memory\__init__.py; P09.13 regression in tests\test_memory.py |
| ✅ Done | P09.14 | Rank stale facts lower during recall | smriti\memory\__init__.py; P09.14 regression in tests\test_memory.py |
| ✅ Done | P09.15 | Show freshness state in recall results | smriti\memory\__init__.py; P09.15 regression in tests\test_memory.py |
| ✅ Done | P09.16 | Handle revalidation without losing history | smriti\memory\__init__.py; P09.16 regression in tests\test_memory.py |
| ✅ Done | P09.17 | Detect contradiction candidates by subject | smriti\memory\__init__.py; P09.17 regression in tests\test_memory.py |
| ✅ Done | P09.18 | Combine embedding similarity with anchor overlap | smriti\memory\__init__.py; P09.18 regression in tests\test_memory.py |
| ✅ Done | P09.19 | Implement source-priority conflict rules | smriti\memory\__init__.py; P09.19 regression in tests\test_memory.py |
| ✅ Done | P09.20 | Retain conflicting fact versions for audit | smriti\memory\__init__.py; P09.20 regression in tests\test_memory.py |
| ✅ Done | P09.21 | Test freshness across edits, moves, and deletions | smriti\memory\__init__.py; P09.21 regression in tests\test_memory.py |

### P10 — Bitemporal and versioned memory log

**Window:** Weeks 9–10. **Dependencies:** P09.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P10.01 | Define valid-time interval semantics | smriti\memory\temporal.py; P10.01 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.02 | Define transaction-time interval semantics | smriti\memory\temporal.py; P10.02 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.03 | Store timezone-aware timestamps | smriti\memory\temporal.py; P10.03 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.04 | Represent open-ended intervals | smriti\memory\temporal.py; P10.04 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.05 | Query facts valid at a historical time | smriti\memory\temporal.py; P10.05 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.06 | Query beliefs as of transaction time | smriti\memory\temporal.py; P10.06 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.07 | Record corrections as additive versions | smriti\memory\temporal.py; P10.07 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.08 | Reject invalid temporal intervals | smriti\memory\temporal.py; P10.08 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.09 | Define canonical operation serialization | smriti\memory\operations.py; P10.09 regression in tests\test_memory_operations.py |
| ✅ Done | P10.10 | Hash operations for content addressing | smriti\memory\operations.py; P10.10 regression in tests\test_memory_operations.py |
| ✅ Done | P10.11 | Link operations to parent history | smriti\memory\operations.py; P10.11 regression in tests\test_memory_operations.py |
| ✅ Done | P10.12 | Implement add operation replay | smriti\memory\__init__.py; P10.12 regression in tests\test_memory.py |
| ✅ Done | P10.13 | Implement update operation replay | smriti\memory\__init__.py; P10.13 regression in tests\test_memory.py |
| ✅ Done | P10.14 | Implement invalidate operation replay | smriti\memory\__init__.py; P10.14 regression in tests\test_memory.py |
| ✅ Done | P10.15 | Define forget tombstone and payload-purge policy | smriti\memory\__init__.py; P10.15 regression in tests\test_memory.py |
| ✅ Done | P10.16 | Implement deterministic log replay | smriti\memory\__init__.py; P10.16 regression in tests\test_memory.py |
| ✅ Done | P10.17 | Implement memory history inspection | smriti\memory\__init__.py; P10.17 regression in tests\test_memory.py |
| ✅ Done | P10.18 | Implement memory state diff | smriti\memory\__init__.py; P10.18 regression in tests\test_memory.py |
| ✅ Done | P10.19 | Implement operation revert as new history | smriti\memory\__init__.py; P10.19 regression in tests\test_memory.py |
| ✅ Done | P10.20 | Handle revert of already-reverted operations | smriti\memory\__init__.py; P10.20 regression in tests\test_memory.py |
| ✅ Done | P10.21 | Persist log and materialized view atomically | smriti\memory\__init__.py; P10.21 regression in tests\test_memory.py |
| ✅ Done | P10.22 | Verify replay matches stored state | smriti\memory\__init__.py; P10.22 regression in tests\test_memory.py |
| ✅ Done | P10.23 | Test clock ties and deterministic ordering | smriti\memory\__init__.py; P10.23 regression in tests\test_memory.py |

### P11 — Git branches, merge, and cascading deletion

**Window:** Weeks 11–12. **Dependencies:** P10, P02.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P11.01 | Map repository branches to memory heads | smriti\memory\__init__.py; P11.01 regression in tests\test_memory.py |
| ✅ Done | P11.02 | Track common base memory state | smriti\memory\__init__.py; P11.02 regression in tests\test_memory.py |
| ✅ Done | P11.03 | Create memory branch from current head | smriti\memory\__init__.py; P11.03 regression in tests\test_memory.py |
| ✅ Done | P11.04 | Switch memory state on git checkout | smriti\memory\__init__.py; P11.04 regression in tests\test_memory.py |
| ✅ Done | P11.05 | Handle detached HEAD explicitly | smriti\memory\__init__.py; P11.05 regression in tests\test_memory.py |
| ✅ Done | P11.06 | Handle branch rename and deletion | smriti\memory\__init__.py; P11.06 regression in tests\test_memory.py |
| ✅ Done | P11.07 | Prevent facts leaking across unrelated branches | smriti\memory\__init__.py; P11.07 regression in tests\test_memory.py |
| ✅ Done | P11.08 | Compute three-way memory merge | smriti\memory\__init__.py; P11.08 regression in tests\test_memory.py |
| ✅ Done | P11.09 | Auto-merge disjoint fact additions | smriti\memory\__init__.py; P11.09 regression in tests\test_memory.py |
| ✅ Done | P11.10 | Detect concurrent edits to the same fact | smriti\memory\__init__.py; P11.10 regression in tests\test_memory.py |
| ✅ Done | P11.11 | Detect delete-versus-update conflicts | smriti\memory\__init__.py; P11.11 regression in tests\test_memory.py |
| ✅ Done | P11.12 | Expose unresolved conflicts for user decisions | smriti\memory\__init__.py; P11.12 regression in tests\test_memory.py |
| ✅ Done | P11.13 | Record merge conflict resolutions | smriti\memory\__init__.py; P11.13 regression in tests\test_memory.py |
| ✅ Done | P11.14 | Represent multi-parent merge history | smriti\memory\__init__.py; P11.14 regression in tests\test_memory.py |
| ✅ Done | P11.15 | Revert a merged operation consistently | smriti\memory\__init__.py; P11.15 regression in tests\test_memory.py |
| ✅ Done | P11.16 | Store source-to-derived-fact edges | smriti\memory\__init__.py; P11.16 regression in tests\test_memory.py |
| ✅ Done | P11.17 | Reject derivation cycles | smriti\memory\__init__.py; P11.17 regression in tests\test_memory.py |
| ✅ Done | P11.18 | Traverse transitive deletion dependencies | smriti\memory\__init__.py; P11.18 regression in tests\test_memory.py |
| ✅ Done | P11.19 | Cascade forget by fact ID | smriti\memory\__init__.py; P11.19 regression in tests\test_memory.py |
| ✅ Done | P11.20 | Cascade forget by session or source | smriti\memory\__init__.py; P11.20 regression in tests\test_memory.py |
| ✅ Done | P11.21 | Define shared-source derivation deletion behavior | smriti\memory\__init__.py; P11.21 regression in tests\test_memory.py |
| ✅ Done | P11.22 | Purge forgotten payloads across branches and caches | smriti\memory\__init__.py; P11.22 regression in tests\test_memory.py |
| ✅ Done | P11.23 | Prevent replay or rollback resurrecting purged facts | smriti\memory\__init__.py; P11.23 regression in tests\test_memory.py |
| ✅ Done | P11.24 | Test deletion with diamond derivation graphs | smriti\memory\__init__.py; P11.24 regression in tests\test_memory.py |
| ✅ Done | P11.25 | Test branch, merge, and revert against state oracle | smriti\memory\__init__.py; P11.25 regression in tests\test_memory.py |

### P12 — CLI, MCP, and consistent service

**Window:** Weeks 11–12. **Dependencies:** P08, P11.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P12.01 | Create Typer CLI entry point | smriti/server/cli.py; CLI version test passed |
| ✅ Done | P12.02 | Implement index command | smriti/server/service.py; create/restart/update/delete integration test passed |
| ✅ Done | P12.03 | Implement index status command | smriti/server/status.py; read-only status and indexed CLI tests passed |
| ✅ Done | P12.04 | Implement context command with budget | smriti/server/retrieval.py; strict budget zero and cached-restart integration tests passed |
| ✅ Done | P12.05 | Implement find-symbol command | smriti/server/service.py; symbol lookup graph and restart integration tests passed |
| ✅ Done | P12.06 | Implement callers and callees commands | resolved call graph CLI integration test passed |
| ✅ Done | P12.07 | Implement remember and recall commands | smriti/server/cli.py, MemoryService in smriti/server/service.py; tests/test_memory_cli.py passed |
| ✅ Done | P12.08 | Implement forget command with cascade | smriti/server/cli.py forget; cascade CLI test in tests/test_memory_cli.py passed |
| ✅ Done | P12.09 | Implement memory log and diff commands | smriti memory log/diff; tests/test_memory_cli.py passed |
| ✅ Done | P12.10 | Implement memory revert command | smriti memory revert; double-revert rejection test passed |
| ✅ Done | P12.11 | Implement memory branch and merge commands | smriti memory branch/switch/merge; tests/test_memory_cli.py passed |
| ✅ Done | P12.12 | Integrate official MCP Python SDK | official ClientSession handshake and status tool passed; strict mypy adapter passed |
| ✅ Done | P12.13 | Define validated MCP tool schemas | smriti/server/schemas.py; invalid budgets anchors confidence and forget-target tests passed |
| ✅ Done | P12.14 | Expose context MCP tool | real stdio client retrieved indexed code; token count and invalid budget tests passed |
| ✅ Done | P12.15 | Expose symbol and graph MCP tools | smriti/server/mcp.py find_symbol/callers/callees; stdio test in tests/test_memory_mcp.py passed |
| ✅ Done | P12.16 | Expose memory CRUD MCP tools | smriti/server/mcp.py remember/recall/forget; stdio test passed |
| ✅ Done | P12.17 | Expose memory history MCP tools | smriti/server/mcp.py memory_log/diff/revert/branch/switch/merge; stdio test passed |
| ✅ Done | P12.18 | Serve immutable index snapshots to queries | smriti/server/snapshots.py; snapshot immutability and stale-writer tests passed |
| ✅ Done | P12.19 | Move indexing to background worker process | smriti/server/jobs.py; spawned-worker persisted-snapshot integration test passed |
| ✅ Done | P12.20 | Keep async server responsive during indexing | smriti/server/jobs.py; concurrent event-loop ticker test passed during real indexing |
| ✅ Done | P12.21 | Handle cancellation and worker errors | smriti/server/jobs.py IndexingError and pool replacement; tests/test_background_errors.py passed |
| ✅ Done | P12.22 | Implement graceful shutdown and recovery | smriti/server/jobs.py idempotent close; serve exits cleanly; tests/test_shutdown_recovery.py passed |
| ✅ Done | P12.23 | Define concurrent writer transaction policy | docs/concurrency.md; targeted verification passed |
| ✅ Done | P12.24 | Document coding-agent MCP connection setup | docs/mcp-setup.md; tool list matches registered MCP tools |
| ✅ Done | P12.25 | Verify CLI and MCP return equivalent results | tests/test_cli_mcp_equivalence.py compares symbol, graph, context, recall, log outputs; passed |
| ✅ Done | P12.26 | Run full code retrieval and memory integration demo | scripts/demo_integration.py; tests/test_demo_integration.py passed (index, context, callers, anchored fact goes stale, cascade forget) |

### P13 — CPU evaluation and benchmarks

**Window:** Weeks 1–2 harness; 11–14 runs. **Dependencies:** P12 for full-system runs.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P13.01 | Pin SWE-bench Lite dataset revision | bench/datasets.json; Hugging Face API SHA 6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2 |
| ✅ Done | P13.02 | Pin SWE-bench Verified dataset revision | bench/datasets.json; Hugging Face API SHA c104f840cc67f8b6eec6f759ebc8b2693d585d4a |
| ✅ Done | P13.03 | Create isolated base-commit checkouts | bench/swebench/checkout.py; base-commit isolation test passed |
| ✅ Done | P13.04 | Validate task repository and commit identity | bench/swebench/validation.py; wrong-repo commit and dirty-checkout tests passed |
| ✅ Done | P13.05 | Extract patch ground truth outside indexed tree | bench/swebench/ground_truth.py; changed-context and added-file tests passed |
| ✅ Done | P13.06 | Map changed functions to base-commit symbols | bench/swebench/mapping.py; neighboring nested and added-function cases passed |
| ✅ Done | P13.07 | Define handling of added and deleted functions | docs/evaluation-labels.md; base-commit label policy reviewed |
| ❌ Pending | P13.08 | Prevent patch and post-fix code leakage | — |
| ✅ Done | P13.09 | Implement issue-word grep baseline | bench/swebench/grep_baseline.py; executable semantic assertions passed |
| ✅ Done | P13.10 | Implement lexical-only baseline | bench/swebench/lexical_baseline.py; executable semantic assertions passed |
| ✅ Done | P13.11 | Implement embedding-only baseline | bench/swebench/embedding_baseline.py; executable semantic assertions passed |
| ✅ Done | P13.12 | Implement Aider-style repo-map baseline | bench/swebench/repo_map_baseline.py; executable semantic assertions passed |
| ✅ Done | P13.13 | Compute file recall at k | bench/swebench/metrics.py; independent duplicate and empty-gold checks passed |
| ✅ Done | P13.14 | Compute function recall at k | bench/swebench/function_metrics.py; duplicate missing empty and negative-k tests passed |
| ✅ Done | P13.15 | Compute packed budget recall at 4k tokens | bench/swebench/budget_metrics.py; executable semantic assertions passed |
| ✅ Done | P13.16 | Compute packed budget recall at 8k tokens | tests/test_budget_metrics.py; executable semantic assertions passed |
| ✅ Done | P13.17 | Compute packed budget recall at 16k tokens | tests/test_budget_metrics.py; executable semantic assertions passed |
| ✅ Done | P13.18 | Measure tokens required to cover gold locations | bench/swebench/budget_metrics.py; executable semantic assertions passed |
| ✅ Done | P13.19 | Separate validation from held-out evaluation | bench/swebench/splits.py; executable semantic assertions passed |
| ❌ Pending | P13.20 | Run component ablations | — |
| ❌ Pending | P13.21 | Record retrieval failures and uncertainty | — |
| ✅ Done | P13.22 | Pin LongMemEval revision and usage terms | bench/longmemeval/manifest.json; HF revision 98d7416c, MIT, SHA-256 d6f21ea9 verified locally |
| ✅ Done | P13.23 | Implement LongMemEval session ingestion adapter | bench/longmemeval/runner.py ingest; tests/test_longmemeval_adapter.py passed (labels and future sessions excluded) |
| ✅ Done | P13.24 | Define retrieval-only memory relevance labels | docs/longmemeval.md: answer_session_ids as binary gold, answer/has_answer never ingested |
| ✅ Done | P13.25 | Evaluate temporal updates and abstention retrieval | bench/longmemeval/results: 500/500 questions; session recall@5 0.848 overall, knowledge-update 0.968, temporal-reasoning 0.655, abstention 0.756; empty-retrieval abstention rate 0.0 |
| ❌ Pending | P13.26 | Separate optional answer-generation scoring | — |
| ✅ Done | P13.27 | Choose licensed repositories for commit replay | bench/codemem/repositories.json; pinned LICENSE SHA-256 and Apache-2.0 verification |
| ✅ Done | P13.28 | Select and record 200-commit replay sequences | requests-200.json contains exactly 200 unique parent-linked public commits; three tamper/count tests; strict mypy and ruff |
| ✅ Done | P13.29 | Create anchored fact injection fixtures | bench/codemem/injection.py; bench/codemem/results/injection.json; injection fixture tests pass |
| ✅ Done | P13.30 | Label expected staleness after each commit | bench/codemem/labels.py; bench/codemem/replay.py; results/labels.jsonl 12,736 labels over 200 real requests commits; tests/test_codemem_labels.py passed |
| ✅ Done | P13.31 | Measure stale detection precision and recall | bench/codemem/results/metrics.json: TP 87, FP 0, FN 0, TN 12649; precision 1.0, recall 1.0 on 64 probes x 199 steps; tests/test_codemem_metrics.py passed |
| ✅ Done | P13.32 | Measure anchor survival through renames | bench/codemem/renames.py; results/rename_survival.json: 64/64 anchors survive real file moves, 64/64 identifier renames conservatively flagged not fresh |
| ✅ Done | P13.33 | Measure cascade deletion correctness | bench/codemem/results/metrics.json cascade: exact diamond closure (4/4 ids), 0 resurrected across 201 memory branches, operation log verifies; bench/codemem/README.md |
| ✅ Done | P13.34 | Publish commit-replay dataset construction scripts | bench/codemem/README.md reproduction commands; bench/codemem/manifest.py, replay.py; replay re-run from a fresh clone reproduced injection.json byte-for-byte |
| ❌ Pending | P13.35 | Measure cold indexing time and peak memory | — |
| ❌ Pending | P13.36 | Measure incremental update p50 and p95 | — |
| ❌ Pending | P13.37 | Measure query p50 and p95 latency | — |
| ✅ Done | P13.38 | Record CPU, RAM, OS, seeds, and configs | bench/swebench/hardware.py; actual CPU, RAM and positive process RSS verified; run config/seed recorded per report |
| ❌ Pending | P13.39 | Export raw results and reproduction commands | — |
| ❌ Pending | P13.40 | Fill result tables only from measured runs | — |

### P14 — UI, documentation, demo, and release

**Window:** Weeks 15–16. **Dependencies:** P12, P13.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P14.01 | Choose minimal UI framework and local API | docs/ui-design.md; view and mutation contracts reviewed |
| ✅ Done | P14.02 | Implement repository index status view | tests/test_ui.py passed; real indexed fixture; JS syntax checked |
| ✅ Done | P14.03 | Implement searchable symbol graph view | 2 real repository UI tests passed; JS syntax checked |
| ✅ Done | P14.04 | Implement packed-context explanation view | 3 real repository UI tests passed; strict budget and blank query checks; JS syntax checked |
| ✅ Done | P14.05 | Implement memory freshness view | 4 real repository UI tests passed; source-edit freshness regression; JS syntax checked |
| ✅ Done | P14.06 | Implement memory history and diff view | 5 real repository UI tests passed; actual before/after memory diff; JS syntax checked |
| ✅ Done | P14.07 | Implement merge conflict resolution view | 6 actual repository UI tests passed; conflict409 and recorded resolution validated; JS syntax checked |
| ✅ Done | P14.08 | Bind local service safely by default | 8 UI tests pass; strict mypy; Ruff; JavaScript syntax |
| ❌ Pending | P14.09 | Expand README with verified setup commands | — |
| ✅ Done | P14.10 | Document architecture and storage formats | docs/architecture.md data flow and every index.sqlite/memory.sqlite table checked against CREATE TABLE statements |
| ❌ Pending | P14.11 | Document memory temporal and deletion semantics | — |
| ❌ Pending | P14.12 | Document limitations and prior work | — |
| ❌ Pending | P14.13 | Document benchmark reproduction | — |
| ✅ Done | P14.14 | Review third-party dependency and model licenses | docs/licenses.md from installed package metadata; model manifest pins tokenizer.json SHA-256 (verified against local artifact) |
| ✅ Done | P14.15 | Verify package name availability before publication | docs/release.md: smriti-engine 404 on PyPI JSON and simple index (2026-10-02); smriti and smriti-mcp taken |
| ❌ Pending | P14.16 | Build and test Python package artifact | — |
| ❌ Pending | P14.17 | Create optional Docker build | — |
| ❌ Pending | P14.18 | Verify clean-install CLI and MCP smoke tests | — |
| ✅ Done | P14.19 | Script cold-index and one-line-edit demo | 20 files cold 2.307s; one changed file edit 0.209s; strict mypy and Ruff |
| ✅ Done | P14.20 | Script issue retrieval within 8k-token budget | Real service functional demo selected101 cl100k tokens within8000; strict mypy and Ruff |
| ✅ Done | P14.21 | Script memory recall across sessions | Closed and reopened actual SQLite store; recalled same ID anchor and session; strict mypy and Ruff |
| ✅ Done | P14.22 | Script rename, stale detection, branch, merge, revert | Real parser rename preserves identity; stale hash detected; conflict blocks; explicit merge and revert verified; strict mypy and Ruff |
| ✅ Done | P14.23 | Record demo video with real timing evidence | Four actual demos rerun;20secondVP9 WebM35106bytes; final PNG visually checked; Ruff; full timing JSON |
| ❌ Pending | P14.24 | Write project report and benchmark findings | — |
| ❌ Pending | P14.25 | Fill resume bullet numbers from published results | — |
| ❌ Pending | P14.26 | Prepare interview answers with algorithm tradeoffs | — |
| ❌ Pending | P14.27 | Tag release after required phases are complete | — |

### P15 — Optional extensions

**Window:** After core release. **Dependencies:** P14.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P15.01 | Add Go parser and resolution support | smriti/parse/languages.py; smriti/resolve/languages.py; docs/languages.md; tests/test_parse_languages.py and tests/test_parse.py passed; tree-sitter pinned <0.26 per docs/parser-compatibility.md |
| ✅ Done | P15.02 | Add C/C++ parser and resolution support | smriti/parse/languages.py; smriti/resolve/languages.py; docs/languages.md; tests/test_parse_languages.py and tests/test_parse.py passed; tree-sitter pinned <0.26 per docs/parser-compatibility.md |
| ✅ Done | P15.03 | Implement cross-language API edges | smriti/resolve/api.py; docs/languages.md; tests/test_resolve_api.py passed |
| ✅ Done | P15.04 | Profile candidate Rust hot path | bench/vector/native_profile.py cProfile: vector.math.distance 46.39s of 48.30s (96%) building/querying 120x384 HNSW |
| ✅ Done | P15.05 | Implement Rust and PyO3 optimization | native/ PyO3 0.29.3 distance kernel, Cargo.lock; built with Rust 1.99.0 via pip install ./native |
| ✅ Done | P15.06 | Compare speedup with identical correctness checks | bench/vector/native_profile.json: 6.69x (18.78s -> 2.81s), identical seeded graph and query IDs, distance parity 1e-12; docs/native-experiment.md |
| ✅ Done | P15.07 | Evaluate push-based approximate PageRank | smriti/rank/push.py residual L1 bound; tests/test_rank_push.py passed against power iteration |
| ✅ Done | P15.08 | Train CPU ranking model without evaluation leakage | smriti/rank/learned.py fit_validation rejects held-out IDs; tests/test_rank_learned.py passed; strict mypy |
| ✅ Done | P15.09 | Design signed memory-log synchronization | smriti/memory/sync.py HMAC-SHA256 bundles; docs/memory.md offline synchronization; tests/test_memory_sync.py authentication, rewind and active-branch tests passed |
| ✅ Done | P15.10 | Test synchronization conflicts between teammates | tests/test_memory_sync.py divergent edits, tombstones, resurrection and merge-base tests passed; smriti/memory/__init__.py single-pass common base |
| ❌ Pending | P15.11 | Create VS Code anchored-memory extension | — |
| ❌ Pending | P15.12 | Implement optional local-model summaries | — |
| ✅ Done | P15.13 | Evaluate memory compression without losing provenance | bench/codemem/results/compression.json: real replay log 379,929 -> 79,465 bytes (0.209), byte-identical, provenance and HMAC preserved; tests/test_memory_sync.py passed |
| ❌ Pending | P15.14 | Implement optional coding-agent task-success comparison | — |
