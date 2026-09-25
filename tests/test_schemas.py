import pytest
from pydantic import ValidationError

from smriti.server.schemas import AnchorInput, ContextRequest, ForgetRequest, RememberRequest


def test_context_rejects_blank_fractional_negative_and_unknown_fields() -> None:
    for values in (
        {'task': '  '},
        {'task': 'fix', 'budget': -1},
        {'task': 'fix', 'budget': 1.5},
        {'task': 'fix', 'other': 'ignored'},
    ):
        with pytest.raises(ValidationError):
            ContextRequest.model_validate(values)
    assert ContextRequest(task='fix', budget=0).budget == 0


def test_memory_confidence_and_hash_are_validated() -> None:
    with pytest.raises(ValidationError):
        RememberRequest(fact='remember', confidence=float('nan'))
    with pytest.raises(ValidationError):
        AnchorInput(symbol_id='s', content_hash='not-a-hash')


def test_forget_requires_one_unambiguous_target() -> None:
    with pytest.raises(ValidationError):
        ForgetRequest()
    with pytest.raises(ValidationError):
        ForgetRequest(fact_id='id', session='session')
    assert ForgetRequest(source='tool').source == 'tool'
