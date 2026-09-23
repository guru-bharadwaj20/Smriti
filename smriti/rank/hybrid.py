"""Deterministic query normalization, fusion, and graph propagation."""
import unicodedata
def normalize_query(query):
    return ' '.join(unicodedata.normalize('NFKC',query).split()).casefold()

def lexical_candidates(index,query,k=50):
    return index.search(normalize_query(query),k)
