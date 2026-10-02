# SWE-bench failures, misses and uncertainty

Configuration `559fae87…39a8`, held-out and validation splits combined unless
stated. Source: `bench/swebench/results/report.json` and the raw rows in
`bench/swebench/results/raw.jsonl`.

## Scope

| Repository | Tasks in Lite ∪ Verified | Measured | Failed |
| --- | --- | --- | --- |
| psf/requests | 13 | 12 | 1 |
| pallets/flask | 4 | 4 | 0 |
| mwaskom/seaborn | 6 | 0 | 6 |
| All other repositories | 684 | not attempted | — |

16 of 707 unique evaluations are measured (2.3%). Results describe two small
libraries and do not represent SWE-bench as a whole.

## Tooling failures

Failures stay failures; none is converted to a zero or excluded silently.

| Task | Stage | Cause |
| --- | --- | --- |
| mwaskom/seaborn (all 6) | checkout | `git clone` failed: GitHub was unreachable from this machine for the rest of the session |
| psf__requests-1724 | retrieval_build | Windows `PermissionError: Access is denied` while atomically renaming the retrieval cache directory into place; a retry was not possible under the same configuration |

The requests failure points at a real robustness gap: on Windows, a directory
rename can fail transiently while another process (for example an antivirus
scanner) holds a handle in the build directory. The retrieval cache should retry
the rename before failing the query.

## Retrieval misses

On 10 of 15 held-out tasks, the full pipeline placed no gold function in its top
10 (every gold set has exactly one function). In 9 of those 10, the correct file
was in the top 10; the miss was choosing the function within the file.

| Task | File in top 10 | BM25 function in top 10 |
| --- | --- | --- |
| pallets__flask-5063 | yes | no |
| pallets__flask-5014 | yes | no |
| psf__requests-6028 | yes | no |
| psf__requests-2317 | no | no |
| psf__requests-2674 | yes | no |
| psf__requests-1142 | yes | no |
| psf__requests-3362 | yes | no |
| psf__requests-1921 | yes | no |
| psf__requests-863 | yes | no |
| psf__requests-2148 | yes | yes |

BM25 also missed 9 of these 10. Three examples, read from the issue texts and
gold patches, show the pattern: the issue names a user-visible symptom while the
fix is in a function whose name shares no words with it.

- requests-6028 reports "error 407" with proxies; the fix is in
  `prepend_scheme_if_needed` in `utils.py`.
- requests-1142 reports GET always sending `content-length`; the fix is in
  `PreparedRequest.prepare_body`.
- flask-5014 asks for an error on empty Blueprint names; the fix is in
  `Blueprint.__init__`, one of many methods in a large class.

## Uncertainty

Paired bootstrap over held-out tasks (2,000 resamples, seed 0) for the
difference in function recall@10:

| Comparison | Mean difference | 95% interval |
| --- | --- | --- |
| full − BM25 | −0.067 | [−0.233, 0.067] |
| full − exact embedding | −0.067 | [−0.300, 0.100] |

Both intervals include zero: with 15 tasks the data cannot distinguish the full
pipeline from either baseline on ranking. The validation split has a single task
and is not interpreted.
