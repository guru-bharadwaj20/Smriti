# Smriti Anchored Memory

Shows Smriti memory facts as CodeLens above the definitions they are anchored to,
marked fresh (✓), stale (⚠) or orphaned (✗), and records new facts anchored to
the definition under the cursor.

Requires the `smriti` CLI (`pip install smriti-engine`) on PATH or set in
`smriti.executable`, and an indexed workspace (`smriti index`).

- **Smriti: Remember Fact About This Symbol** saves, re-indexes, and anchors the
  fact to the current content hash of the enclosing definition.
- **Smriti: Re-index and Refresh Memory** re-indexes so edited code turns facts stale.

Build: `npm install`, `npm test`, `npm run package`.

Integration test (downloads an isolated VS Code; needs an indexed workspace with
one fact anchored to `parse_header` in `app.py`):
`npm run test:integration -- <workspace>`.
