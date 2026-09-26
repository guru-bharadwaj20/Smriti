# Concurrent writers and consistent readers

Index readers begin a SQLite read transaction and materialize one immutable
snapshot of symbols, edges, file digests, and version. Queries retain their snapshot
while an index update runs. WAL lets readers continue while the writer commits.

Writers prepare changes against an expected version and enter BEGIN IMMEDIATE.
A stale expected version raises ConcurrentUpdateError; the caller must reload and
retry the computation. Busy writers wait up to 30 seconds then surface the error.
Index and memory databases have separate transactions; freshness synchronization
must carry an index version and be replayable after a crash between stores.

Snapshot tests verify retained views, stale writer rejection, rollback on a SQL
failure midway through an update, and reopening after an abrupt process exit.
