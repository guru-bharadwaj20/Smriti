import pytest

from bench.longmemeval.answers import score

ROWS = [
    {'question_id': 'q1', 'question_type': 'single-session-user', 'answer': 'The Blue Lagoon'},
    {'question_id': 'q2', 'question_type': 'temporal-reasoning', 'answer': '3 days'},
    {'question_id': 'q3_abs', 'question_type': 'multi-session', 'answer': 'not mentioned'},
]


def test_scores_normalized_answers_and_abstention_separately():
    result = score(
        ROWS,
        {'q1': 'You visited blue lagoon.', 'q2': 'About 4 days', 'q3_abs': "I don't know that."},
    )
    assert result['official_llm_judge'] is False
    assert result['accuracy']['all'] == pytest.approx(2 / 3)
    assert result['accuracy']['abstention'] == 1.0
    assert result['accuracy']['temporal-reasoning'] == 0.0


def test_partial_hypotheses_and_unknown_ids():
    assert score(ROWS, {'q1': 'blue lagoon'})['answered_questions'] == 1
    with pytest.raises(ValueError):
        score(ROWS, {'missing': 'x'})
