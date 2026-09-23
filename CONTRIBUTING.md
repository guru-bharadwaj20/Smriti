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
| ❌ Pending | P01.12 | Configure CI for supported platforms | — |
| ❌ Pending | P01.13 | Define config file and environment precedence | — |
| ❌ Pending | P01.14 | Define ignored paths and local data directory | — |
| ❌ Pending | P01.15 | Create small repository fixtures with known symbols | — |
| ❌ Pending | P01.16 | Document setup and contributor commands | — |
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
| ❌ Pending | P02.09 | Detect created files | — |
| ❌ Pending | P02.10 | Detect modified files | — |
| ❌ Pending | P02.11 | Detect deleted files | — |
| ❌ Pending | P02.12 | Detect unchanged-content file moves | — |
| ❌ Pending | P02.13 | Connect filesystem watcher | — |
| ❌ Pending | P02.14 | Debounce repeated events | — |
| ❌ Pending | P02.15 | Coalesce checkout event bursts | — |
| ❌ Pending | P02.16 | Schedule affected-file indexing jobs | — |
| ❌ Pending | P02.17 | Diff old and new symbol sets | — |
| ❌ Pending | P02.18 | Preserve symbol IDs for verified renames | — |
| ❌ Pending | P02.19 | Remove dangling graph references after deletion | — |
| ❌ Pending | P02.20 | Update postings and vectors for changed symbols | — |
| ❌ Pending | P02.21 | Commit index changes atomically | — |
| ❌ Pending | P02.22 | Recover from interrupted indexing | — |
| ❌ Pending | P02.23 | Verify incremental and fresh-index equivalence | — |
| ❌ Pending | P02.24 | Measure one-line update latency on stated hardware | — |

### P03 — Parsing and symbol extraction

**Window:** Weeks 3–5. **Dependencies:** P01.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P03.01 | Integrate tree-sitter parser lifecycle | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.02 | Extract Python module scopes | smriti/parse; pytest tests/test_parse.py passed |
| ✅ Done | P03.03 | Extract Python class definitions | smriti/parse; pytest tests/test_parse.py passed |
| ❌ Pending | P03.04 | Extract Python functions and methods | — |
| ❌ Pending | P03.05 | Extract signatures and docstrings | — |
| ❌ Pending | P03.06 | Capture byte offsets and source line ranges | — |
| ❌ Pending | P03.07 | Extract import declarations | — |
| ❌ Pending | P03.08 | Extract call expression candidates | — |
| ❌ Pending | P03.09 | Extract inheritance declarations | — |
| ❌ Pending | P03.10 | Model nested definitions and comprehensions | — |
| ❌ Pending | P03.11 | Store parser diagnostics for invalid syntax | — |
| ❌ Pending | P03.12 | Reuse syntax trees for edited files | — |
| ❌ Pending | P03.13 | Handle unicode offsets and line endings | — |
| ❌ Pending | P03.14 | Chunk source at symbol boundaries | — |
| ❌ Pending | P03.15 | Define treatment of oversized functions | — |
| ❌ Pending | P03.16 | Add TypeScript extraction fixtures | — |
| ❌ Pending | P03.17 | Implement TypeScript symbol extraction | — |
| ❌ Pending | P03.18 | Add Java extraction fixtures | — |
| ❌ Pending | P03.19 | Implement Java symbol extraction | — |
| ❌ Pending | P03.20 | Validate symbol ranges against source slices | — |
| ❌ Pending | P03.21 | Document staged Go and C/C++ support | — |

### P04 — Scope-aware resolution and graph

**Window:** Weeks 6–8; hardening 9–10. **Dependencies:** P02, P03.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ❌ Pending | P04.01 | Build scope parent links | — |
| ❌ Pending | P04.02 | Resolve local bindings | — |
| ❌ Pending | P04.03 | Resolve enclosing-scope bindings | — |
| ❌ Pending | P04.04 | Resolve module-level names | — |
| ❌ Pending | P04.05 | Resolve aliased imports | — |
| ❌ Pending | P04.06 | Resolve relative imports | — |
| ❌ Pending | P04.07 | Resolve re-exported names within supported scope | — |
| ❌ Pending | P04.08 | Record builtins and external references | — |
| ❌ Pending | P04.09 | Resolve self method calls | — |
| ❌ Pending | P04.10 | Implement Python C3 linearisation | — |
| ❌ Pending | P04.11 | Resolve inherited methods | — |
| ❌ Pending | P04.12 | Respect overridden methods | — |
| ❌ Pending | P04.13 | Record uncertain dynamic-call candidates | — |
| ❌ Pending | P04.14 | Assign confidence to resolved edges | — |
| ❌ Pending | P04.15 | Persist defines and contains edges | — |
| ❌ Pending | P04.16 | Persist calls and imports edges | — |
| ❌ Pending | P04.17 | Persist inheritance edges | — |
| ❌ Pending | P04.18 | Define test-to-symbol association rules | — |
| ❌ Pending | P04.19 | Expose callers and callees graph queries | — |
| ❌ Pending | P04.20 | Create hand-labelled call-edge fixtures | — |
| ❌ Pending | P04.21 | Compare resolution with pyright or jedi | — |
| ❌ Pending | P04.22 | Report edge precision and recall | — |
| ❌ Pending | P04.23 | Document unresolved dynamic-language cases | — |

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
| ❌ Pending | P05.12 | Implement BM25F field weighting | — |
| ❌ Pending | P05.13 | Encode posting deltas | — |
| ❌ Pending | P05.14 | Implement variable-byte encoding | — |
| ❌ Pending | P05.15 | Implement posting decoding | — |
| ❌ Pending | P05.16 | Add symbols incrementally | — |
| ❌ Pending | P05.17 | Remove symbols and update statistics | — |
| ❌ Pending | P05.18 | Persist and reload lexical index | — |
| ❌ Pending | P05.19 | Define deterministic tie breaking | — |
| ❌ Pending | P05.20 | Validate scoring against hand-computed examples | — |
| ❌ Pending | P05.21 | Benchmark lexical query time and storage | — |

### P06 — CPU embeddings and custom HNSW

**Window:** Weeks 6–10. **Dependencies:** P03, P05.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ❌ Pending | P06.01 | Select and record embedding model license | — |
| ❌ Pending | P06.02 | Pin model artifact and checksum | — |
| ❌ Pending | P06.03 | Configure ONNX CPU inference | — |
| ❌ Pending | P06.04 | Evaluate int8 embedding quality | — |
| ❌ Pending | P06.05 | Batch symbol embedding requests | — |
| ❌ Pending | P06.06 | Cache embeddings by content and model version | — |
| ✅ Done | P06.07 | Normalize vectors for chosen distance metric | smriti/vector/math.py; smriti/vector/__init__.py; executable assertions passed |
| ✅ Done | P06.08 | Persist vectors in memory-mapped storage | smriti/vector/storage.py; executable assertions passed |
| ✅ Done | P06.09 | Implement exact nearest-neighbor oracle | smriti/vector/math.py; executable assertions passed |
| ✅ Done | P06.10 | Implement seeded random level assignment | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.11 | Implement HNSW entry point management | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.12 | Implement upper-layer greedy descent | smriti/vector/hnsw.py; executable assertions passed |
| ✅ Done | P06.13 | Implement candidate queue search | smriti/vector/hnsw.py; executable assertions passed |
| ❌ Pending | P06.14 | Implement neighbor selection heuristic | — |
| ❌ Pending | P06.15 | Implement bidirectional graph insertion | — |
| ❌ Pending | P06.16 | Enforce neighbor count limits | — |
| ❌ Pending | P06.17 | Implement efConstruction configuration | — |
| ❌ Pending | P06.18 | Implement efSearch configuration | — |
| ❌ Pending | P06.19 | Exclude tombstoned vectors from results | — |
| ❌ Pending | P06.20 | Implement deletion repair or rebuild strategy | — |
| ❌ Pending | P06.21 | Update embeddings after source edits | — |
| ❌ Pending | P06.22 | Persist and reload HNSW graph | — |
| ❌ Pending | P06.23 | Validate graph invariants after updates | — |
| ❌ Pending | P06.24 | Compare recall at 10 against exact search | — |
| ❌ Pending | P06.25 | Compare quality and throughput with hnswlib | — |
| ❌ Pending | P06.26 | Measure memory and CPU query latency | — |

### P07 — Hybrid retrieval and graph ranking

**Window:** Weeks 6–8; integration 11–12. **Dependencies:** P04, P05, P06.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P07.01 | Define query normalization | smriti/rank/__init__.py; smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.02 | Retrieve lexical candidates | smriti/rank/hybrid.py; executable assertions passed |
| ✅ Done | P07.03 | Retrieve vector candidates | smriti/rank/hybrid.py; executable assertions passed |
| ❌ Pending | P07.04 | Implement reciprocal rank fusion | — |
| ❌ Pending | P07.05 | Define graph edge type weights | — |
| ❌ Pending | P07.06 | Include resolution confidence in weights | — |
| ❌ Pending | P07.07 | Build sparse adjacency representation | — |
| ❌ Pending | P07.08 | Normalize transitions and handle dangling nodes | — |
| ❌ Pending | P07.09 | Seed personalized restart distribution | — |
| ❌ Pending | P07.10 | Implement PageRank power iteration | — |
| ❌ Pending | P07.11 | Specify convergence and iteration limits | — |
| ❌ Pending | P07.12 | Test ranking on a hand-computed graph | — |
| ❌ Pending | P07.13 | Expand candidate set with callers | — |
| ❌ Pending | P07.14 | Include associated tests and configuration | — |
| ❌ Pending | P07.15 | Cache ranking with index-version keys | — |
| ❌ Pending | P07.16 | Invalidate cache after index updates | — |
| ❌ Pending | P07.17 | Tune fusion weights on validation data only | — |
| ❌ Pending | P07.18 | Emit per-candidate selection explanations | — |

### P08 — Token-budgeted context packing

**Window:** Weeks 9–10. **Dependencies:** P07.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P08.01 | Define omitted symbol representation | smriti/pack/__init__.py; smriti/pack/packer.py; executable assertions passed |
| ❌ Pending | P08.02 | Define name and path representation | — |
| ❌ Pending | P08.03 | Define signature and docstring representation | — |
| ❌ Pending | P08.04 | Define full-body representation | — |
| ❌ Pending | P08.05 | Integrate chosen model tokenizer | — |
| ❌ Pending | P08.06 | Count rendering overhead and metadata tokens | — |
| ❌ Pending | P08.07 | Reserve budget for memory and response framing | — |
| ❌ Pending | P08.08 | Assign values to representation levels | — |
| ❌ Pending | P08.09 | Implement multiple-choice knapsack dynamic program | — |
| ❌ Pending | P08.10 | Implement bucketed budget option | — |
| ❌ Pending | P08.11 | Implement greedy marginal-value baseline | — |
| ❌ Pending | P08.12 | Require minimum class context for methods | — |
| ❌ Pending | P08.13 | Deduplicate class and method bodies | — |
| ❌ Pending | P08.14 | Handle dependency costs during packing | — |
| ❌ Pending | P08.15 | Handle symbols larger than available budget | — |
| ❌ Pending | P08.16 | Render stable file and symbol ordering | — |
| ❌ Pending | P08.17 | Render omitted-line markers | — |
| ❌ Pending | P08.18 | Recount final rendered output tokens | — |
| ❌ Pending | P08.19 | Enforce strict final budget limit | — |
| ❌ Pending | P08.20 | Compare small instances with exhaustive oracle | — |
| ❌ Pending | P08.21 | Measure packing quality and latency | — |
| ❌ Pending | P08.22 | Document approximation limits under constraints | — |

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
| ❌ Pending | P09.10 | Mark deleted anchors orphaned | — |
| ❌ Pending | P09.11 | Follow verified symbol renames | — |
| ❌ Pending | P09.12 | Record freshness reason and triggering commit | — |
| ❌ Pending | P09.13 | Define policy for memories with multiple anchors | — |
| ❌ Pending | P09.14 | Rank stale facts lower during recall | — |
| ❌ Pending | P09.15 | Show freshness state in recall results | — |
| ❌ Pending | P09.16 | Handle revalidation without losing history | — |
| ❌ Pending | P09.17 | Detect contradiction candidates by subject | — |
| ❌ Pending | P09.18 | Combine embedding similarity with anchor overlap | — |
| ❌ Pending | P09.19 | Implement source-priority conflict rules | — |
| ❌ Pending | P09.20 | Retain conflicting fact versions for audit | — |
| ❌ Pending | P09.21 | Test freshness across edits, moves, and deletions | — |

### P10 — Bitemporal and versioned memory log

**Window:** Weeks 9–10. **Dependencies:** P09.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P10.01 | Define valid-time interval semantics | smriti\memory\temporal.py; P10.01 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.02 | Define transaction-time interval semantics | smriti\memory\temporal.py; P10.02 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.03 | Store timezone-aware timestamps | smriti\memory\temporal.py; P10.03 regression in tests\test_memory_temporal.py |
| ✅ Done | P10.04 | Represent open-ended intervals | smriti\memory\temporal.py; P10.04 regression in tests\test_memory_temporal.py |
| ❌ Pending | P10.05 | Query facts valid at a historical time | — |
| ❌ Pending | P10.06 | Query beliefs as of transaction time | — |
| ❌ Pending | P10.07 | Record corrections as additive versions | — |
| ❌ Pending | P10.08 | Reject invalid temporal intervals | — |
| ✅ Done | P10.09 | Define canonical operation serialization | smriti\memory\operations.py; P10.09 regression in tests\test_memory_operations.py |
| ✅ Done | P10.10 | Hash operations for content addressing | smriti\memory\operations.py; P10.10 regression in tests\test_memory_operations.py |
| ✅ Done | P10.11 | Link operations to parent history | smriti\memory\operations.py; P10.11 regression in tests\test_memory_operations.py |
| ❌ Pending | P10.12 | Implement add operation replay | — |
| ❌ Pending | P10.13 | Implement update operation replay | — |
| ❌ Pending | P10.14 | Implement invalidate operation replay | — |
| ❌ Pending | P10.15 | Define forget tombstone and payload-purge policy | — |
| ❌ Pending | P10.16 | Implement deterministic log replay | — |
| ❌ Pending | P10.17 | Implement memory history inspection | — |
| ❌ Pending | P10.18 | Implement memory state diff | — |
| ❌ Pending | P10.19 | Implement operation revert as new history | — |
| ❌ Pending | P10.20 | Handle revert of already-reverted operations | — |
| ❌ Pending | P10.21 | Persist log and materialized view atomically | — |
| ❌ Pending | P10.22 | Verify replay matches stored state | — |
| ❌ Pending | P10.23 | Test clock ties and deterministic ordering | — |

### P11 — Git branches, merge, and cascading deletion

**Window:** Weeks 11–12. **Dependencies:** P10, P02.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ❌ Pending | P11.01 | Map repository branches to memory heads | — |
| ❌ Pending | P11.02 | Track common base memory state | — |
| ❌ Pending | P11.03 | Create memory branch from current head | — |
| ❌ Pending | P11.04 | Switch memory state on git checkout | — |
| ❌ Pending | P11.05 | Handle detached HEAD explicitly | — |
| ❌ Pending | P11.06 | Handle branch rename and deletion | — |
| ❌ Pending | P11.07 | Prevent facts leaking across unrelated branches | — |
| ❌ Pending | P11.08 | Compute three-way memory merge | — |
| ❌ Pending | P11.09 | Auto-merge disjoint fact additions | — |
| ❌ Pending | P11.10 | Detect concurrent edits to the same fact | — |
| ❌ Pending | P11.11 | Detect delete-versus-update conflicts | — |
| ❌ Pending | P11.12 | Expose unresolved conflicts for user decisions | — |
| ❌ Pending | P11.13 | Record merge conflict resolutions | — |
| ❌ Pending | P11.14 | Represent multi-parent merge history | — |
| ❌ Pending | P11.15 | Revert a merged operation consistently | — |
| ❌ Pending | P11.16 | Store source-to-derived-fact edges | — |
| ❌ Pending | P11.17 | Reject derivation cycles | — |
| ❌ Pending | P11.18 | Traverse transitive deletion dependencies | — |
| ❌ Pending | P11.19 | Cascade forget by fact ID | — |
| ❌ Pending | P11.20 | Cascade forget by session or source | — |
| ❌ Pending | P11.21 | Define shared-source derivation deletion behavior | — |
| ❌ Pending | P11.22 | Purge forgotten payloads across branches and caches | — |
| ❌ Pending | P11.23 | Prevent replay or rollback resurrecting purged facts | — |
| ❌ Pending | P11.24 | Test deletion with diamond derivation graphs | — |
| ❌ Pending | P11.25 | Test branch, merge, and revert against state oracle | — |

### P12 — CLI, MCP, and consistent service

**Window:** Weeks 11–12. **Dependencies:** P08, P11.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ❌ Pending | P12.01 | Create Typer CLI entry point | — |
| ❌ Pending | P12.02 | Implement index command | — |
| ❌ Pending | P12.03 | Implement index status command | — |
| ❌ Pending | P12.04 | Implement context command with budget | — |
| ❌ Pending | P12.05 | Implement find-symbol command | — |
| ❌ Pending | P12.06 | Implement callers and callees commands | — |
| ❌ Pending | P12.07 | Implement remember and recall commands | — |
| ❌ Pending | P12.08 | Implement forget command with cascade | — |
| ❌ Pending | P12.09 | Implement memory log and diff commands | — |
| ❌ Pending | P12.10 | Implement memory revert command | — |
| ❌ Pending | P12.11 | Implement memory branch and merge commands | — |
| ❌ Pending | P12.12 | Integrate official MCP Python SDK | — |
| ❌ Pending | P12.13 | Define validated MCP tool schemas | — |
| ❌ Pending | P12.14 | Expose context MCP tool | — |
| ❌ Pending | P12.15 | Expose symbol and graph MCP tools | — |
| ❌ Pending | P12.16 | Expose memory CRUD MCP tools | — |
| ❌ Pending | P12.17 | Expose memory history MCP tools | — |
| ✅ Done | P12.18 | Serve immutable index snapshots to queries | smriti/server/snapshots.py; snapshot immutability and stale-writer tests passed |
| ❌ Pending | P12.19 | Move indexing to background worker process | — |
| ❌ Pending | P12.20 | Keep async server responsive during indexing | — |
| ❌ Pending | P12.21 | Handle cancellation and worker errors | — |
| ❌ Pending | P12.22 | Implement graceful shutdown and recovery | — |
| ❌ Pending | P12.23 | Define concurrent writer transaction policy | — |
| ❌ Pending | P12.24 | Document coding-agent MCP connection setup | — |
| ❌ Pending | P12.25 | Verify CLI and MCP return equivalent results | — |
| ❌ Pending | P12.26 | Run full code retrieval and memory integration demo | — |

### P13 — CPU evaluation and benchmarks

**Window:** Weeks 1–2 harness; 11–14 runs. **Dependencies:** P12 for full-system runs.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ✅ Done | P13.01 | Pin SWE-bench Lite dataset revision | bench/datasets.json; Hugging Face API SHA 6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2 |
| ✅ Done | P13.02 | Pin SWE-bench Verified dataset revision | bench/datasets.json; Hugging Face API SHA c104f840cc67f8b6eec6f759ebc8b2693d585d4a |
| ✅ Done | P13.03 | Create isolated base-commit checkouts | bench/swebench/checkout.py; base-commit isolation test passed |
| ❌ Pending | P13.04 | Validate task repository and commit identity | — |
| ❌ Pending | P13.05 | Extract patch ground truth outside indexed tree | — |
| ❌ Pending | P13.06 | Map changed functions to base-commit symbols | — |
| ❌ Pending | P13.07 | Define handling of added and deleted functions | — |
| ❌ Pending | P13.08 | Prevent patch and post-fix code leakage | — |
| ❌ Pending | P13.09 | Implement issue-word grep baseline | — |
| ❌ Pending | P13.10 | Implement lexical-only baseline | — |
| ❌ Pending | P13.11 | Implement embedding-only baseline | — |
| ❌ Pending | P13.12 | Implement Aider-style repo-map baseline | — |
| ✅ Done | P13.13 | Compute file recall at k | bench/swebench/metrics.py; independent duplicate and empty-gold checks passed |
| ❌ Pending | P13.14 | Compute function recall at k | — |
| ❌ Pending | P13.15 | Compute packed budget recall at 4k tokens | — |
| ❌ Pending | P13.16 | Compute packed budget recall at 8k tokens | — |
| ❌ Pending | P13.17 | Compute packed budget recall at 16k tokens | — |
| ❌ Pending | P13.18 | Measure tokens required to cover gold locations | — |
| ❌ Pending | P13.19 | Separate validation from held-out evaluation | — |
| ❌ Pending | P13.20 | Run component ablations | — |
| ❌ Pending | P13.21 | Record retrieval failures and uncertainty | — |
| ❌ Pending | P13.22 | Pin LongMemEval revision and usage terms | — |
| ❌ Pending | P13.23 | Implement LongMemEval session ingestion adapter | — |
| ❌ Pending | P13.24 | Define retrieval-only memory relevance labels | — |
| ❌ Pending | P13.25 | Evaluate temporal updates and abstention retrieval | — |
| ❌ Pending | P13.26 | Separate optional answer-generation scoring | — |
| ❌ Pending | P13.27 | Choose licensed repositories for commit replay | — |
| ❌ Pending | P13.28 | Select and record 200-commit replay sequences | — |
| ❌ Pending | P13.29 | Create anchored fact injection fixtures | — |
| ❌ Pending | P13.30 | Label expected staleness after each commit | — |
| ❌ Pending | P13.31 | Measure stale detection precision and recall | — |
| ❌ Pending | P13.32 | Measure anchor survival through renames | — |
| ❌ Pending | P13.33 | Measure cascade deletion correctness | — |
| ❌ Pending | P13.34 | Publish commit-replay dataset construction scripts | — |
| ❌ Pending | P13.35 | Measure cold indexing time and peak memory | — |
| ❌ Pending | P13.36 | Measure incremental update p50 and p95 | — |
| ❌ Pending | P13.37 | Measure query p50 and p95 latency | — |
| ❌ Pending | P13.38 | Record CPU, RAM, OS, seeds, and configs | — |
| ❌ Pending | P13.39 | Export raw results and reproduction commands | — |
| ❌ Pending | P13.40 | Fill result tables only from measured runs | — |

### P14 — UI, documentation, demo, and release

**Window:** Weeks 15–16. **Dependencies:** P12, P13.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ❌ Pending | P14.01 | Choose minimal UI framework and local API | — |
| ❌ Pending | P14.02 | Implement repository index status view | — |
| ❌ Pending | P14.03 | Implement searchable symbol graph view | — |
| ❌ Pending | P14.04 | Implement packed-context explanation view | — |
| ❌ Pending | P14.05 | Implement memory freshness view | — |
| ❌ Pending | P14.06 | Implement memory history and diff view | — |
| ❌ Pending | P14.07 | Implement merge conflict resolution view | — |
| ❌ Pending | P14.08 | Bind local service safely by default | — |
| ❌ Pending | P14.09 | Expand README with verified setup commands | — |
| ❌ Pending | P14.10 | Document architecture and storage formats | — |
| ❌ Pending | P14.11 | Document memory temporal and deletion semantics | — |
| ❌ Pending | P14.12 | Document limitations and prior work | — |
| ❌ Pending | P14.13 | Document benchmark reproduction | — |
| ❌ Pending | P14.14 | Review third-party dependency and model licenses | — |
| ❌ Pending | P14.15 | Verify package name availability before publication | — |
| ❌ Pending | P14.16 | Build and test Python package artifact | — |
| ❌ Pending | P14.17 | Create optional Docker build | — |
| ❌ Pending | P14.18 | Verify clean-install CLI and MCP smoke tests | — |
| ❌ Pending | P14.19 | Script cold-index and one-line-edit demo | — |
| ❌ Pending | P14.20 | Script issue retrieval within 8k-token budget | — |
| ❌ Pending | P14.21 | Script memory recall across sessions | — |
| ❌ Pending | P14.22 | Script rename, stale detection, branch, merge, revert | — |
| ❌ Pending | P14.23 | Record demo video with real timing evidence | — |
| ❌ Pending | P14.24 | Write project report and benchmark findings | — |
| ❌ Pending | P14.25 | Fill resume bullet numbers from published results | — |
| ❌ Pending | P14.26 | Prepare interview answers with algorithm tradeoffs | — |
| ❌ Pending | P14.27 | Tag release after required phases are complete | — |

### P15 — Optional extensions

**Window:** After core release. **Dependencies:** P14.

| Status | ID | Subtask | Evidence |
| --- | --- | --- | --- |
| ❌ Pending | P15.01 | Add Go parser and resolution support | — |
| ❌ Pending | P15.02 | Add C/C++ parser and resolution support | — |
| ❌ Pending | P15.03 | Implement cross-language API edges | — |
| ❌ Pending | P15.04 | Profile candidate Rust hot path | — |
| ❌ Pending | P15.05 | Implement Rust and PyO3 optimization | — |
| ❌ Pending | P15.06 | Compare speedup with identical correctness checks | — |
| ❌ Pending | P15.07 | Evaluate push-based approximate PageRank | — |
| ❌ Pending | P15.08 | Train CPU ranking model without evaluation leakage | — |
| ❌ Pending | P15.09 | Design signed memory-log synchronization | — |
| ❌ Pending | P15.10 | Test synchronization conflicts between teammates | — |
| ❌ Pending | P15.11 | Create VS Code anchored-memory extension | — |
| ❌ Pending | P15.12 | Implement optional local-model summaries | — |
| ❌ Pending | P15.13 | Evaluate memory compression without losing provenance | — |
| ❌ Pending | P15.14 | Implement optional coding-agent task-success comparison | — |
