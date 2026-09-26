# Local inspection UI

Install the optional UI dependencies and start it from your repository:

```sh
python -m pip install -e '.[ui]'
python -m smriti.ui . --port 8765
```

Open `http://127.0.0.1:8765`. The bundled interface reads the same index and memory
used by CLI and MCP. It displays actual index counts, definitions and graph edges,
packed context with selection explanations, anchored fact freshness, memory history
and state diffs, and three-way merge conflicts. A merge applies only after the user
chooses a source and explicitly clicks Apply merge. Missing conflict resolutions
return HTTP 409.

The launcher accepts only loopback listeners. HTTP host validation rejects other
hostnames, mutations reject a foreign browser origin, and responses use `no-store`.
There are no remote scripts, fonts, or CDN dependencies. Source code and facts are
inserted with DOM text nodes rather than interpreted as HTML.

The default HTTP port is 8765. CLI/MCP indexing remains available while the UI is
open; refresh a view to read the latest published snapshot.
