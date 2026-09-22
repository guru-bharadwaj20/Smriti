"""Identifier-aware tokenization with deterministic Unicode normalization."""
import re
def tokenize(text: str) -> list[str]:
    return [part.casefold() for word in re.findall(r"\w+", text) for chunk in word.split("_") for part in re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+|[^\W\d_]+", chunk) if part]


def identifier_tokens(text: str) -> list[str]:
    """Retain complete identifiers alongside their constituent words."""
    return tokenize(text) + [word.casefold() for word in re.findall(r"\w+", text) if "_" in word or len(tokenize(word)) > 1]


STOP_WORDS = {"python": frozenset("def class return pass import from as if else elif for while try except finally with yield lambda global nonlocal del assert raise break continue and or not in is None True False".casefold().split()), "typescript": frozenset("function class return let const var import export interface type new extends implements".split()), "java": frozenset("public private protected static final class return new extends implements package import void".split())}

def code_tokens(text: str, language: str = "python") -> list[str]:
    return [word for word in identifier_tokens(text) if word not in STOP_WORDS.get(language, frozenset())]
