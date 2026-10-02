# LongMemEval retrieval-only evaluation

Smriti evaluates LongMemEval-S (cleaned) as a memory retrieval benchmark. It does
not generate answers, so its numbers are not comparable with the published
answer-accuracy leaderboard.

## Pinned input

`bench/longmemeval/manifest.json` pins `xiaowu0162/longmemeval-cleaned` at revision
`98d7416c24c778c2fee6e6f3006e7a073259d48f`, file `longmemeval_s_cleaned.json`
(277,383,467 bytes, SHA-256 `d6f21ea9…c3a442`). The dataset card declares the MIT
license. The runner refuses any file whose size or digest differs, and it requires
all 500 unique question IDs.

## Relevance labels

| Field | Use |
| --- | --- |
| `haystack_sessions`, `haystack_session_ids`, `haystack_dates` | Ingested: one memory fact per session, `valid_from` set to the session date |
| `question`, `question_date` | Query text and `valid_at` time for recall |
| `answer_session_ids` | Gold relevance labels. A retrieved session is relevant exactly when its ID is listed |
| `answer`, per-turn `has_answer` | Never ingested or read during retrieval |
| `question_type` | Grouping key for per-category reports |

Each session is relevant or not relevant; no graded relevance is inferred. Every
gold ID appears in its question's haystack. `session_recall_at_5` is the fraction
of gold sessions among the top five recalled facts. Facts whose valid time starts
after `question_date` cannot be returned, so future sessions never count.

## Temporal updates and abstention

`knowledge-update` and `temporal-reasoning` rows are reported as separate groups
because they test whether the most recent valid fact is retrieved. Questions whose
ID ends in `_abs` (30 rows) carry a false premise. Their `answer_session_ids` still
name the related evidence sessions, so they receive recall scores like any other
row. `abstention_retrieval_rate` additionally reports how often recall returned
nothing. Lexical recall rarely returns an empty list, so this rate is expected to
be low; it is a retrieval signal, not an LLM abstention judgement.

## Answer generation

`answer_accuracy` is always `null` in retrieval summaries. Answer-generation
scoring is optional and lives in `bench/longmemeval/answers.py`; it requires
externally produced hypotheses and is reported separately.
