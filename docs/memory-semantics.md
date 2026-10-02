# Memory temporal and deletion semantics

This is the precise contract for what `recall` returns and what each mutation
does. Every example below is executed by `tests/test_memory_semantics_doc.py`.
API reference and storage layout live in [memory.md](memory.md) and
[architecture.md](architecture.md).

## Two time axes

| Axis | Fields | Question it answers | Set by |
| --- | --- | --- | --- |
| Valid time | `valid_from`, `valid_to` | When is the fact true about the code or project? | Caller (`valid_from=`, `valid_to=`); defaults to recording time |
| Transaction time | `recorded_at`, `superseded_at` | When did the store believe it? | Store clock; never caller-editable |

Both are half-open intervals `[start, end)`; a `null` end is open. All timestamps
must carry a UTC offset; naive times are rejected with `ValueError`.

| Call | Returns |
| --- | --- |
| `recall()` | Current beliefs on the active branch |
| `recall(valid_at=t)` | Versions whose valid interval contains `t`, as currently believed |
| `recall(as_of=t)` | What the store believed at transaction time `t` |
| `recall(valid_at=t1, as_of=t2)` | Both filters together |
| `recall(include_stale=False)` | Drops `stale` and `orphaned` facts |

```python
store.remember('timeout is 30s', fact_id='timeout', valid_from='2026-01-01T00:00:00+00:00')
store.update('timeout', 'timeout is 60s', valid_from='2026-03-01T00:00:00+00:00')
store.recall()                                   # ['timeout is 60s']
store.recall(valid_at='2026-02-01T00:00:00+00:00')  # ['timeout is 30s']
store.recall(as_of=<time before the update>)      # ['timeout is 30s']
store.recall(valid_at='2025-12-31T00:00:00+00:00')  # []  (before it became true)
```

`update()` is a correction: it closes the earlier version's valid interval at the
new `valid_from` and records a new version. Nothing is overwritten, so earlier
beliefs remain queryable with `as_of`.

## Mutations

| Operation | Effect on current view | History | Reversible |
| --- | --- | --- | --- |
| `remember` | Adds a fact | `add` operation | Yes, via `revert` |
| `update` | Replaces current text/interval | `update` operation; old version kept | Yes |
| `invalidate` | Removes the fact from the branch | `invalidate` operation; payload kept | Yes |
| `revert(op)` | Restores the state before `op` | New `revert` operation | Reverting the same operation twice raises |
| `forget(id)` | Removes the fact and every derived fact everywhere | Payload erased; tombstone kept | Never |

`invalidate` means "no longer true". `forget` means "must not exist", for
example a leaked secret or personal data.

```python
store.remember('uses sqlite', fact_id='db')
store.invalidate('db')           # recall() == []
store.revert(<invalidate op>)    # recall() == ['uses sqlite']; log has 3 operations
store.revert(<invalidate op>)    # ValueError: already reverted
```

## Forgetting

`forget(fact_id)` purges the fact and all transitive dependents in the derivation
DAG (diamonds included), returning their IDs. It applies to every branch, not
just the active one. Payload blobs and audit text are deleted, SQLite
`secure_delete` overwrites freed pages, and the WAL is checkpointed. Operation
records keep only hashes. A `memory_purged` tombstone then blocks the ID from
returning through revert, replay, merge, branch switch or an imported bundle.

```python
store.remember('raw note', fact_id='src')
store.remember('summary of note', fact_id='derived', derived_from=['src'])
store.forget('src')               # ['derived', 'src']
store.switch(<any branch>)        # neither fact is visible
store.revert(<add of src>)        # ValueError: Forgotten payloads cannot be restored
store.forget('src')               # []  (idempotent)
```

`forget_by(session=..., source=...)` applies the same purge to every fact with
that provenance. Copies outside `memory.sqlite`, such as backups or exported
bundles, remain the operator's responsibility.

## Freshness

Anchored facts carry `(symbol_id, content_hash)` pairs. After each index,
`refresh(current_hashes, renames=...)` updates freshness:

| State | Condition |
| --- | --- |
| `fresh` | Every anchor's symbol exists with the recorded hash |
| `stale` | An anchored symbol exists but its hash changed |
| `orphaned` | An anchored symbol no longer exists |

A rename moves an anchor only when the destination hash equals the recorded
hash, so a file move keeps facts fresh while a renamed function (whose body
text changes) does not. A fact never becomes fresh again by itself, even if the
code is reverted: `revalidate()` records an explicit confirmation. Unanchored
project facts have no freshness checks and stay `fresh` until corrected.
Measured on real history: 200 Requests commits gave stale-detection precision and
recall of 1.0, and 64/64 anchors survived file moves
([bench/codemem/README.md](../bench/codemem/README.md)).

## Branches and merges

Each Git branch maps to a memory branch (`sync_git`). Facts added on one branch are
invisible on unrelated branches. `merge(source, resolutions=...)` performs a
three-way merge against the common base: disjoint additions merge automatically;
concurrent edits or delete-versus-update conflicts must be resolved explicitly
with `ours`, `theirs`, `base` or `delete`. A merge is a two-parent operation and can
itself be reverted.
