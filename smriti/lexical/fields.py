"""Explicit retrieval fields independent of parser implementation."""

from smriti.models import Symbol


def symbol_fields(symbol: Symbol) -> dict[str, str]:
    return {'signature': symbol.signature, 'docstring': symbol.docstring or '', 'body': symbol.body}
