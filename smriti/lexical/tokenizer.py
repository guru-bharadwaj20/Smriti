"""Identifier-aware tokenization with deterministic Unicode normalization."""

import re


def tokenize(text: str) -> list[str]:
    """Split snake identifiers; keep duplicates to preserve term frequency."""
    return [part for word in re.findall(r"\w+", text) for chunk in word.split("_") for part in re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+|[^\W\d_]+", chunk) if part]



def identifier_tokens(text: str) -> list[str]:
    """Retain complete identifiers alongside their constituent words."""
    return tokenize(text) + [word for word in re.findall(r"\w+", text) if "_" in word or len(tokenize(word)) > 1]
