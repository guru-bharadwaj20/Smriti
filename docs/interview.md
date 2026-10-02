# Design questions and trade-offs

Short answers to the questions this project most often raises, with the reason
behind each choice and what it costs. Numbers come from the committed results.

## Indexing

**Why a Merkle tree instead of file modification times?**
mtimes change on checkout, copy and touch without content changing, and can stay
the same after a fast edit. Content hashes make "changed" exact, and directory
hashes let a branch switch skip whole unchanged subtrees. The cost is hashing
every file once on a cold start.

**How are symbol IDs kept stable?**
An ID is `sha256(repo, path, kind, qualname)`, so it is stable while a definition
stays in place. A move is reconciled only when exactly one removed and one added
symbol share a content hash. Ambiguous cases (two identical functions) are left
unreconciled rather than guessed. On real Requests code, 64/64 anchors survived
file moves.

## Retrieval

**Why BM25F and vectors and a graph, rather than embeddings alone?**
Identifiers like `parse_header` are exact-match signals that embeddings blur; issue
text describes behavior that lexical search misses; and the function to change is
often a caller or callee of what the issue names. Reciprocal rank fusion combines
lists without calibrating their score scales, and personalized PageRank (damping
0.85) spreads relevance from the fused seeds along call, import and inheritance
edges weighted by resolution confidence. Each component's contribution is measured
by ablation (no vectors, no graph) on SWE-bench.

**Why write HNSW instead of using hnswlib or FAISS?**
To control determinism (seeded levels), deletion with tombstones, persistence
format and invariants checked in tests. Recall@10 is compared against an exact
oracle and hnswlib. The cost is speed: pure-Python distance takes 96% of the
time, which is why the optional Rust kernel exists (6.7x faster, identical graph).
Parameters are m=16, efConstruction=100, efSearch=50.

**BM25 parameters?**
k1=1.2, b=0.75 with per-field weights for signature, docstring and body. Fusion
weights were grid-searched on a separate synthetic validation fixture with its own
held-out IDs. SWE-bench tasks are split into validation and held-out sets by a hash
of the instance ID (shared by Lite and Verified), and held-out tasks are never used
for tuning.

## Packing

**Why a knapsack instead of "top-k until the budget is full"?**
Each symbol can appear at four detail levels (omitted, name, signature+docstring,
full body), and the best context often mixes a few full bodies with many
signatures. Multiple-choice knapsack DP is exact for independent items. Methods
carry their class signature as a dependency, which can double-count shared
context; that is conservative (never over budget) but not globally optimal. A
greedy baseline is kept for comparison, and the final text is always recounted with
the real tokenizer so the budget is a hard limit.

## Memory

**Why anchor facts to content hashes?**
Agent memory goes wrong silently when the code it describes changes. Recording the
hash of the exact definition makes staleness a cheap equality check after each
index. Over 200 real commits it detected every changed anchor with no false alarms
(precision and recall 1.0). The limit: it detects that code changed, not whether
the claim is still true.

**Why two time axes?**
Valid time answers "when was this true?" and transaction time answers "when did we
believe it?". Corrections close an interval instead of overwriting, so you can ask
what the agent believed before a fix, which matters for debugging agent behavior.

**Why model memory history like Git (operation DAG, branches, merges)?**
Code branches diverge, so knowledge about them must too: facts learned on a
feature branch should not leak to main until merged. Content-addressed operations
make replay deterministic and verifiable. Three-way merges surface conflicting
edits instead of picking a winner silently.

**How is deletion made real?**
`forget` traverses the derivation DAG (including diamonds), erases payloads, uses
SQLite secure delete and WAL checkpointing, and leaves a tombstone so no replay,
revert, merge or synchronized bundle can bring the fact back. Revert and
invalidate, by contrast, are reversible history. The cost is that forgotten facts
cannot be audited by content later, only by hash.

## Evaluation

**How do you avoid fooling yourself on SWE-bench?**
Index only the base commit, query only the issue text, and check before every task
that the query contains no diff and the index contains no post-fix lines. Empty
gold is reported as undefined, not 100%. Failures stay failures. Results are split
into validation and held-out sets, with paired bootstrap intervals.

**Why build a separate commit-replay benchmark?**
No public benchmark measures whether code-anchored memory notices when code
changes. CodeMem replays 200 pinned commits of Requests, labels expected freshness
from indexed hashes independently of the memory store, and publishes the labels.

## What I would do next

Semantic staleness (does the change contradict the fact, not just touch its
code), compiler-backed resolution for typed languages, a larger multi-repository
CodeMem, and running the full 707-task SWE-bench on faster hardware.
