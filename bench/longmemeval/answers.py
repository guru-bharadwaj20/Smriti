"""Optional answer-generation scoring, separate from retrieval evaluation.

Smriti generates no answers. This module scores hypotheses produced elsewhere
(one JSON object per line: ``{"question_id": ..., "hypothesis": ...}``) against
the pinned dataset's reference answers with deterministic normalized matching.
The official LongMemEval protocol uses an LLM judge; these scores are a
reproducible lower-fidelity proxy and must never be reported as official accuracy.
"""

from __future__ import annotations

import argparse
import json
import re
import string
from collections import defaultdict
from pathlib import Path
from typing import Any

ABSTENTION = re.compile(
    r"\b(i (do not|don't) know|not (mentioned|enough information)|cannot (answer|determine)"
    r'|no information|did not mention|never mentioned)\b'
)


def normalize(text: str) -> str:
    text = text.lower().translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\b(a|an|the)\b', ' ', text)
    return ' '.join(text.split())


def correct(row: dict[str, Any], hypothesis: str) -> bool:
    if str(row['question_id']).endswith('_abs'):
        return bool(ABSTENTION.search(hypothesis.lower()))
    reference = normalize(str(row['answer']))
    return bool(reference) and reference in normalize(hypothesis)


def score(rows: list[dict[str, Any]], hypotheses: dict[str, str]) -> dict[str, Any]:
    unknown = sorted(set(hypotheses) - {str(row['question_id']) for row in rows})
    if unknown:
        raise ValueError(f'Hypotheses for unknown questions: {unknown[:3]}')
    groups: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        identity = str(row['question_id'])
        if identity not in hypotheses:
            continue
        outcome = correct(row, hypotheses[identity])
        groups['all'].append(outcome)
        groups[str(row['question_type'])].append(outcome)
        if identity.endswith('_abs'):
            groups['abstention'].append(outcome)
    return {
        'method': 'normalized reference containment; abstention phrase match for _abs',
        'official_llm_judge': False,
        'answered_questions': len(groups['all']),
        'total_questions': len(rows),
        'accuracy': {
            name: sum(values) / len(values) for name, values in sorted(groups.items()) if values
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('hypotheses', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.dataset.read_text(encoding='utf-8'))
    hypotheses = {}
    for line in args.hypotheses.read_text(encoding='utf-8').splitlines():
        if line.strip():
            record = json.loads(line)
            hypotheses[str(record['question_id'])] = str(record['hypothesis'])
    args.output.write_text(json.dumps(score(rows, hypotheses), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
