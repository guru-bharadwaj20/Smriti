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

def test_ties_are_stable():
    x=BM25Index()
    for id in ['z','a','m']: x.add(id,{'body':'same'})
    assert [hit.id for hit in x.search('same')]==['a','m','z']

def test_hand_computed_score():
    assert abs(bm25_score(1,1,1,1,1)-math.log(4/3))<1e-12
    assert abs(bm25_score(2,1,2,2,2)-math.log(2)*4.4/3.2)<1e-12
    assert posting_ids(encode(deltas([1,128,20000]))) == [1,128,20000]
