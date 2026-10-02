# Optional Docker image

The `Dockerfile` builds a wheel in a throwaway stage and installs only that wheel
into `python:3.12-slim` with `git` (needed for memory branch tracking). It runs
as an unprivileged `smriti` user with `/repo` as the working directory. Model
weights are never baked in.

```sh
docker build -t smriti-engine:0.1.0 .
docker run --rm -v "$PWD:/repo" smriti-engine:0.1.0 index
docker run --rm -v "$PWD:/repo" smriti-engine:0.1.0 context "fix header parsing" --budget 8000
docker run --rm -i -v "$PWD:/repo" smriti-engine:0.1.0 serve      # MCP over stdio
```

State is written to `/repo/.smriti` on the mounted repository, exactly as with a
local install. For vector retrieval, mount downloaded weights and set
`SMRITI_MODEL_DIR`:
`-v ~/smriti-models:/models:ro -e SMRITI_MODEL_DIR=/models` (also needs the
`vectors` extra; the default image is lexical + graph only).

Verified 2 October 2026 with Docker Engine 29.1.3 in WSL2 Ubuntu 24.04: the
image builds (542 MB), `smriti version` prints `0.1.0`, and
`docker run --rm -w /tmp --entrypoint python smriti-engine:0.1.0 /opt/smriti/smoke_install.py`
passes the CLI and MCP stdio smoke test with all 14 tools listed.

On Windows, building straight from a `/mnt/c` checkout can fail when a cache
directory is unreadable from WSL; build from a clean copy (or `git archive`) of
the repository instead.
