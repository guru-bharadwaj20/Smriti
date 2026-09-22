# Memory schema contract

A fact has an immutable ID, text, optional subject, finite confidence in [0,1],
source provenance (user, session, tool), and zero or more code anchors.
An anchor records symbol ID and the content hash observed when the fact was made.
Unanchored project facts remain valid until corrected; absence of anchors is
explicit, not a claim that source changes were checked.

Each fact version has a half-open valid interval [valid_from, valid_to) and a
half-open transaction interval [recorded_at, superseded_at). All times carry UTC
offsets. Open ends are null. Historical queries select both dimensions independently.
Corrections create new versions rather than changing historical beliefs.

The content-addressed operation DAG stores canonical operations and parent IDs.
Branch heads select views; merges have multiple parents and unresolved conflicts
are exposed rather than silently choosing a winner. Derivation edges form a DAG.
Forget is irreversible payload erasure across all branches and derived facts;
history may retain non-sensitive tombstones, never erased text or source payload.
Revert is additive history and cannot resurrect forgotten payloads.
