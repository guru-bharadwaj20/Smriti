"""Explicit retrieval fields independent of parser implementation."""
def symbol_fields(symbol):
    return {"signature": symbol.signature, "docstring": symbol.docstring or "", "body": symbol.body}
