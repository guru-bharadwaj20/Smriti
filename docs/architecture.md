# Architecture and storage formats

## Components and data flow

```
 watcher ──► Merkle scan ──► parser ──► resolver ──► IndexStore (index.sqlite)
 (watch/)    (merkle/)       (parse/)   (resolve/)        │ immutable snapshot
                                                          ▼
 task ──► BM25F (lexical/) ┐                       Retriever (server/retrieval.py)
          HNSW  (vector/)  ├─► RRF + personalized PageRank (rank/) ─► packer (pack/)
                           ┘                                              │
 MemoryStore (memory.sqlite) ── fresh facts ──► context preamble ─────────┘
        ▲  refresh(current hashes) after every index
 CLI (server/cli.py) · MCP (server/mcp.py) · UI (ui/app.py) ──► SmritiService / MemoryService
```

1. `RepositoryScanner` hashes files bottom-up into a Merkle tree, honouring
   `.gitignore` and always excluding the state directory. Only changed leaves
   are reparsed.
2. `SourceParser` extracts symbols with tree-sitter (Python, TypeScript, Java, Go,
   C, C++), reusing the previous tree for edited files.
3. `Resolver` builds scope chains and emits `defines`, `contains`, `calls`,
   `may_call`, `imports`, `inherits` and `tests` edges with confidence weights.
4. `SmritiService.index()` publishes a new snapshot version atomically. Queries
   always read one complete snapshot.
5. `Retriever` builds (or loads from cache) the BM25F and HNSW indexes for a
   snapshot version, fuses candidates with reciprocal rank fusion, expands them
   over the graph with personalized PageRank, and packs representations with a
   multiple-choice knapsack under a strict tokenizer budget.
6. `MemoryStore` is an independent operation log. After indexing, current
   symbol hashes refresh anchor freshness. Fresh facts that match the task are
   prepended to context within a quarter of the budget.

CLI, MCP and UI adapters call the same service methods; `tests/test_cli_mcp_equivalence.py`
checks that they return identical results.

## State directory

The default state directory is `.smriti/` in the repository root (override with
`data_dir` in `smriti.toml` or `SMRITI_DATA_DIR`). Everything below is local,
regenerable from source except `memory.sqlite`, and excluded from indexing.

| Path | Format | Contents |
| --- | --- | --- |
| `repository-id` | text | 32 hex characters, created once; part of every symbol ID |
| `index.sqlite` | SQLite, WAL | Published code index (tables below) |
| `retrieval/<version>-<key>/` | directory | `lexical.json` (BM25F postings), `hnsw.json` (graph), `complete.json` marker. Built in a private `.build-*` directory and renamed into place |
| `embeddings.sqlite` | SQLite | `embeddings(key, vector)` cache keyed by content hash and model version |
| `memory.sqlite` | SQLite, `secure_delete=ON` | Memory facts and operation log (tables below). The only state that cannot be rebuilt |
| `models/` | ONNX + `tokenizer.json` | Optional, downloaded explicitly and checked against `smriti/vector/model_manifest.json` |

### index.sqlite

| Table | Columns | Notes |
| --- | --- | --- |
| `metadata` | `key`, `value` | `version` increments on every published snapshot |
| `symbols` | `id`, `payload` | `payload` is sorted-key JSON of `smriti.models.Symbol` |
| `edges` | `source`, `target`, `kind`, `confidence` | Primary key `(source, target, kind)` |
| `files` | `path`, `digest` | SHA-256 of each indexed file; drives incremental updates |

Symbol IDs are `sha256(repository_id \0 path \0 kind \0 qualname)`. A verified
move keeps the existing ID. Content hashes are SHA-256 of the symbol's exact source
bytes.

### memory.sqlite

| Table | Columns | Notes |
| --- | --- | --- |
| `facts` | `id`, `payload` | Materialized view of the active branch; canonical JSON fact |
| `fact_anchors` | `fact_id`, `symbol_id`, `content_hash` | Hash observed when the fact was recorded |
| `memory_operations` | `seq`, `oid`, `canonical` | Content-addressed operation DAG; `oid` = SHA-256 of `canonical` |
| `memory_blobs` | `digest`, `payload` | Fact payloads referenced by operations; erased on forget |
| `memory_branches` | `name`, `head` | Branch heads; Git refs map to branches through `sync_git` |
| `memory_derivations` | `source_id`, `derived_id` | Derivation DAG used for cascading forget |
| `memory_purged` | `fact_id` | Tombstones that block resurrection through replay, merge or revert |
| `fact_audit`, `conflict_audit` | | Version and conflict-resolution audit trail |
| `memory_meta` | `key`, `value` | Active `branch` name and current `head` operation |

Canonical JSON uses sorted keys and compact separators, so equal operations
always hash identically. Replaying `memory_operations` from the root reproduces
`facts`; `MemoryStore.verify()` checks this.

Memory bundles exchanged between teammates (`smriti.memory.sync`) are canonical
JSON documents authenticated with HMAC-SHA256 and optionally zlib-compressed.
