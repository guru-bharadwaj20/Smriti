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


def test_incremental_matches_fresh_index():
    import random
    rng=random.Random(35)
    live={}
    incremental=BM25Index()
    for _ in range(80):
        id=str(rng.randrange(12))
        if rng.random()<0.3:
            live.pop(id,None); incremental.remove(id)
        else:
            fields={'signature':rng.choice(['load user','save user','']),'body':rng.choice(['config token','password settings',''])}
            live[id]=fields; incremental.add(id,fields)
        fresh=BM25Index()
        for key,fields in live.items(): fresh.add(key,fields)
        assert incremental.lengths==fresh.lengths
        assert incremental.averages==fresh.averages
        assert incremental.document_frequency==fresh.document_frequency
        assert incremental.search('user config password')==fresh.search('user config password')
