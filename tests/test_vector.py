from smriti.vector.hnsw import HNSWIndex
from smriti.vector.math import exact_search
import random

def test_update():
    x=HNSWIndex()
    x.add('a',[1,0]); x.add('b',[0,1]); x.add('a',[-1,0])
    assert x.search([1,0],1)[0].id=='b'
