"""Deterministic query normalization, fusion, and graph propagation."""
import unicodedata
def normalize_query(query):
    return ' '.join(unicodedata.normalize('NFKC',query).split()).casefold()
