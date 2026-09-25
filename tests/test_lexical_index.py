from smriti.lexical.index import BM25Index, bm25_score
from smriti.lexical.codec import encode, decode, deltas, posting_ids
import math

def test_delete_statistics():
    x=BM25Index()
    x.add('a', {'body':'hello hello'})
    x.add('b', {'body':'hello'})
    x.remove('a')
    assert x.document_frequency=={'hello':1}
    assert x.averages=={'body':1}
    x.remove('b')
    assert x.search('hello')==[]
