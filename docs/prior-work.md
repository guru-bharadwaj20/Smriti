# Prior work and positioning

| Project | Relevant existing capability | Smriti's intended emphasis |
| --- | --- | --- |
| Aider | Repository maps select important signatures using graph ranking and a token budget | Resolved symbol edges, combined lexical/vector search, and anchored memory |
| Cursor | Integrated coding agent with codebase context tooling | A separately usable local service with inspectable algorithms and evaluation |
| Mem0 | Adds and retrieves memory with metadata and scope | Code hash anchors, source-change freshness, and branch-aware history |
| Graphiti / Zep | Temporal knowledge graph for agent memory | Apply temporal memory to code symbols and Git branch/merge workflows |

These projects already solve parts of the problem. Smriti's contribution must be
demonstrated through implementation and measured evaluation. Code-anchored,
git-versioned memory is the central research question; the roadmap makes no
claim that every component is novel or that competing projects lack newer features.

Primary sources reviewed during project setup:

- [Aider repository maps](https://aider.chat/docs/repomap.html)
- [Cursor documentation](https://cursor.com/docs)
- [Mem0 memory addition](https://docs.mem0.ai/core-concepts/memory-operations/add)
- [Graphiti introduction](https://help.getzep.com/graphiti/getting-started/welcome)

## How the comparison is evaluated

Claims against prior work are limited to what Smriti measures directly:

- **Aider-style repository maps.** `bench/swebench/repo_map_baseline.py`
  reimplements the published idea (graph-ranked signatures under a budget) and
  runs beside Smriti on the same SWE-bench tasks. It is a reimplementation, not
  Aider itself.
- **Mem0 / Zep-style memory.** No head-to-head run was performed. Smriti's
  distinguishing behavior, freshness tied to code hashes, is measured on its own
  terms by CodeMem (stale precision/recall 1.0 over 200 real commits) rather than
  against these systems.
- **Cursor.** Closed source; no comparison is attempted.
- **LongMemEval.** Smriti reports retrieval recall only, so its numbers cannot be
  placed on leaderboards that score generated answers.

See [limitations.md](limitations.md) for the boundaries of these results.
