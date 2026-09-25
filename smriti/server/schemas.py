"""Validated requests shared by MCP, CLI, and local HTTP adapters."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class ContextRequest(Request):
    task: str = Field(min_length=1, max_length=50000)
    budget: int = Field(default=8000, ge=0, le=65536)

    @field_validator('task')
    @classmethod
    def meaningful_task(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Task cannot be blank')
        return value


class AnchorInput(Request):
    symbol_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=r'^[0-9a-f]{64}$')


class RememberRequest(Request):
    fact: str = Field(min_length=1, max_length=50000)
    anchors: list[AnchorInput] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0, le=1, allow_inf_nan=False)
    source: str | None = Field(default=None, min_length=1)
    session: str | None = Field(default=None, min_length=1)


class ForgetRequest(Request):
    fact_id: str | None = Field(default=None, min_length=1)
    source: str | None = Field(default=None, min_length=1)
    session: str | None = Field(default=None, min_length=1)

    @model_validator(mode='after')
    def one_target(self) -> 'ForgetRequest':
        if sum(value is not None for value in (self.fact_id, self.source, self.session)) != 1:
            raise ValueError('Choose exactly one fact, source, or session to forget')
        return self


class MergeRequest(Request):
    source: str = Field(min_length=1)
    resolutions: dict[str, Literal['ours', 'theirs', 'base', 'delete']] = Field(
        default_factory=dict
    )
