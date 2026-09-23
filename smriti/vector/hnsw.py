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

    def _refresh_entry(self):
        self.entry=min(self.levels,key=lambda id:(-self.levels[id],id)) if self.levels else None

    def _greedy(self,query,entry,layer):
        best=entry; best_dist=distance(query,self.vectors[best])
        while True:
            candidate=min([best,*self.graph[best].get(layer,())],key=lambda id:(distance(query,self.vectors[id]),id))
            value=distance(query,self.vectors[candidate])
            if value>=best_dist: return best
            best,best_dist=candidate,value

    def _layer_search(self,query,entries,ef,layer):
        visited=set(entries)
        candidates=[(distance(query,self.vectors[id]),id) for id in entries]
        heapq.heapify(candidates)
        best=[(-d,id) for d,id in candidates]; heapq.heapify(best)
        while candidates:
            d,id=heapq.heappop(candidates)
            if len(best)>=ef and d > -best[0][0]: break
            for neighbor in sorted(self.graph[id].get(layer,())):
                if neighbor in visited: continue
                visited.add(neighbor); nd=distance(query,self.vectors[neighbor])
                if len(best)<ef or nd < -best[0][0]:
                    heapq.heappush(candidates,(nd,neighbor)); heapq.heappush(best,(-nd,neighbor))
                    if len(best)>ef: heapq.heappop(best)
        return sorted([( -d,id) for d,id in best])
