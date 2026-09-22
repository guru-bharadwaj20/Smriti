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
