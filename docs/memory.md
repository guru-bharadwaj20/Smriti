# Durable code memory

`MemoryStore(path)` keeps repository facts in SQLite. Each fact can carry explicit
`Anchor(symbol_id, content_hash)` values, provenance, confidence, a valid-time
interval, and derivation parents. Project facts can have no anchors. Call `close()`
after use; each public mutation commits atomically, including derivation edges.

`recall(valid_at=..., as_of=...)` distinguishes when a fact applies from when the
store believed it. Corrections split valid-time intervals and preserve earlier
beliefs. Both query timestamps must include timezone information. Current search
uses BM25 over fact text and ranks fresh matches ahead of stale matches.

`refresh(current_hashes, renames=..., commit=...)` marks changed anchors stale and
missing anchors orphaned. A rename moves an anchor only when its original hash
matches the destination hash. A returned implementation does not silently make an
old belief fresh: `revalidate()` records an explicit confirmation. Fact metadata
records the reason and triggering commit.

## Branches and operations

Each operation has a canonical JSON representation and a SHA-256 identity. Parent
identities form an immutable operation DAG; independent payload blobs support
physical deletion. `branch()`, `switch()`, `log()`, `diff()` and `revert()` expose
the history. `sync_git(repository)` follows the active Git ref or a detached
revision namespace. A new namespace begins from the active memory head, so callers
that traverse history should visit parent revisions before children.

`merge_preview(source)` performs a three-way comparison and reports conflicting
facts. `merge(source, resolutions={id: 'ours'})` records two parents and requires
explicit resolutions for every conflict. Allowed choices are `ours`, `theirs`,
`base`, and `delete`. Multiple incomparable merge bases are rejected for explicit
handling. Reversion records a new operation rather than rewriting history.

## Forgetting and provenance

`invalidate()` removes a belief from the active branch while retaining its past.
`forget()` is an irreversible purge: it traverses derivation edges, including
diamonds, erases payloads and audit text, and prevents deleted identities from
returning through any branch, merge, replay or revert. Immutable operation records
retain hashes rather than deleted text. SQLite secure deletion, WAL checkpointing
and vacuuming erase database payload pages; backups outside this database remain
the caller's responsibility.

Tests cover temporal corrections, merge conflicts, branch isolation, physical
deletion, derivation diamonds, immutable metadata, transaction failure injection
and concurrent forgetting during a derived-fact write.

## Offline synchronization and compression

`smriti.memory.sync.export_bundle(store, repository_id, key)` authenticates the
canonical operation records, payloads, active head, and irreversible tombstones
with HMAC-SHA256. Provision a random key of at least 32 bytes out of band. This is
shared-secret group authentication: every key holder can produce a valid bundle.
It does not prove which teammate authored a fact. Bundles contain memory text;
encrypt the transport or archive separately when confidentiality is required.

`import_bundle(..., branch='peer/alice')` verifies authentication, repository
scope, payload checksums and parent ordering before an atomic import. It creates
or advances a peer branch, rejects rewinds and divergent replacements, and leaves
merge choices explicit. Different teammate edits produce the same three-way
conflicts as local branches. Tombstones apply globally, including locally derived
facts, and an old authenticated bundle cannot restore purged payloads.

`compress_bundle()` uses lossless zlib compression. `decompress_bundle()` rejects
truncated streams, trailing data, and decompression beyond its configured limit.
Compression preserves canonical bytes, temporal metadata, anchors, provenance,
operation identities and authentication. It produces no semantic summaries.
`python -m bench.codemem.compression` measures these properties against the real
commit-replay memory database and records raw and compressed byte counts.
