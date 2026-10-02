# CodeMem commit replay

CodeMem replays real public repository history to evaluate code-anchored memory without an LLM. The initial source is [psf/requests](https://github.com/psf/requests), whose [Apache-2.0 license at the pinned revision](https://github.com/psf/requests/blob/611c6162cbc4ac2020a2f91c7cfa4f3abf9bbb60/LICENSE) was checked against the local clone.

The repositories.json manifest records the source URL, exact revision used for license verification, license path, and license SHA-256. Repository contents remain in an ignored local checkout; published artifacts contain commit references, derived structural labels, facts, and measurements. No source code is relicensed as Smriti.

The replay sequence contains 200 actual first-parent revisions, in ancestor order. Explicit manifest hashes make the selection reproducible. Staleness labels concern implementation changes or missing symbols, rather than the semantic truth of arbitrary natural-language claims. Rename survival requires unique, identical implementation hashes across a symbol identity change.

## Measurements and limitations

The injection fixture selects library functions by a deterministic SHA-256 rank
of their stable symbol identities. Each probe asserts its implementation
fingerprint. Every subsequent commit is checked out and indexed through
`SmritiService.index()`. The oracle labels changes and disappearance directly
from indexed hashes, independently of the memory store's returned freshness.
After scoring a step, probes whose symbols exist are explicitly revalidated
against that implementation for the next step. Source timestamps are retained
as provenance; ancestry determines replay order.

`labels.jsonl` contains per-commit observations. `metrics.json` records the
confusion matrix, precision and recall. A denominator of zero produces `null`,
never an invented perfect score. `renames.json` records only unique matching-hash
identity changes affecting probes; zero eligible renames means rename survival
is unmeasured. A final derivation diamond measures exact cascade closure and
checks all recorded memory branches for resurrection after forgetting.

This benchmark evaluates structural anchor invalidation. It does not establish
the semantic accuracy of arbitrary remembered claims or LLM answer quality.
