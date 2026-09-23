"""From-scratch hierarchical navigable small-world index, cosine metric."""
import heapq,json,math,random
from pathlib import Path
from .math import normalize,distance,VectorHit

class HNSWIndex:
    def __init__(self,m=16,ef_construction=100,ef_search=50,seed=0):
        if m<2 or ef_construction<m or ef_search<1: raise ValueError('invalid HNSW configuration')
        self.m=m; self.ef_construction=ef_construction; self.ef_search=ef_search
        self.seed=seed; self.random=random.Random(seed)
        self.vectors={}; self.levels={}; self.graph={}; self.entry=None; self.deleted=set()
    def random_level(self):
        return min(32,int(-math.log(max(self.random.random(),1e-15))/math.log(self.m)))
