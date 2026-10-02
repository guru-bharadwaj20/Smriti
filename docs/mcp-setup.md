# Connecting a coding agent over MCP

Smriti serves its tools over the official MCP stdio transport. Install it in the
environment the agent will launch, index the repository once, then register the
server command with your agent.

```bash
python -m pip install -e ".[vectors]"
smriti index --root /path/to/repo
smriti serve --root /path/to/repo      # what the agent runs; speaks MCP on stdio
```

## Claude Code

```bash
claude mcp add smriti -- smriti serve --root /path/to/repo
```

## Generic `mcpServers` JSON (Claude Desktop, Cursor, and similar clients)

```json
{
  "mcpServers": {
    "smriti": {
      "command": "smriti",
      "args": ["serve", "--root", "/path/to/repo"]
    }
  }
}
```

Use the absolute path of the virtual environment's `smriti` executable (or
`python -m smriti`) when the agent does not inherit that environment's `PATH`.

## Tools

| Tool | Purpose |
| --- | --- |
| `context(task, budget)` | Ranked code context within a token budget |
| `status()` | Committed index version and coverage |
| `find_symbol(name)`, `callers(name)`, `callees(name)` | Symbol lookup and call graph |
| `remember`, `recall`, `forget` | Fact CRUD; `forget` cascades to derived facts |
| `memory_log`, `memory_diff`, `memory_revert` | Operation history |
| `memory_branch`, `memory_switch`, `memory_merge` | Memory branches; merges report conflicts unless resolved |

State lives in `.smriti/` under the repository (override with `SMRITI_DATA_DIR`).
Re-run `smriti index` after large changes; queries always read the last
committed snapshot, so an interrupted index never serves partial results.
