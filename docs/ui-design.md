# Local inspection UI

The first UI uses FastAPI and a small bundled HTML/CSS/JavaScript client. This
keeps the CPU-only installation independent of a Node build and lets the UI call
the same repository service used by CLI and MCP.

| View | Purpose | Service data |
| --- | --- | --- |
| Repository | See index version and source coverage | Index status |
| Symbols | Search definitions and explore callers/callees | Symbol graph |
| Context | Inspect selected code and its ranking explanation | Context bundle |
| Memory | Search facts and see stale or orphaned anchors | Recall |
| History | Compare memory states and review operations | Log and diff |
| Conflicts | Choose a resolution for each conflicting fact | Merge conflicts |

The API binds to loopback by default. Read views do not mutate state. Index,
remember, forget, revert, and merge-resolution actions are explicit user actions
with visible results. The UI never hides unresolved merge conflicts or removes
freshness warnings from recalled facts. It uses local assets and no external CDN.
