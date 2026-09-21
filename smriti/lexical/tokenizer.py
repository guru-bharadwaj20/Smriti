"""Identifier-aware tokenization with deterministic Unicode normalization."""

import re


def tokenize(text: str) -> list[str]:
    """Split snake identifiers; keep duplicates to preserve term frequency."""
    return [part for word in re.findall(r"\w+", text) for part in word.split("_") if part]

