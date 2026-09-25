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

    def _select(self,query,candidates,limit):
        selected=[]; rejected=[]
        for d,id in sorted(candidates):
            if all(distance(self.vectors[id],self.vectors[other])>=d for other in selected): selected.append(id)
            else: rejected.append(id)
            if len(selected)==limit: return selected
        return (selected+rejected)[:limit]

    def add(self,id,vector):
        value=normalize(vector)
        if self.vectors and len(value)!=len(next(iter(self.vectors.values()))): raise ValueError('dimension mismatch')
        if id in self.vectors:
            self.vectors[id]=value; self.deleted.discard(id); self.rebuild(); return
        level=self.random_level(); self.vectors[id]=value; self.levels[id]=level
        self.graph[id]={layer:set() for layer in range(level+1)}
        if self.entry is None: self.entry=id; return
        entry=self.entry; max_level=self.levels[entry]
        for layer in range(max_level,level,-1): entry=self._greedy(value,entry,layer)
        for layer in range(min(level,max_level),-1,-1):
            candidates=self._layer_search(value,[entry],self.ef_construction,layer)
            neighbors=self._select(value,candidates,self.m)
            for other in neighbors:
                self.graph[id][layer].add(other); self.graph[other][layer].add(id)
            for other in [id,*neighbors]:
                limit=self.m*2 if layer==0 else self.m
                links=self.graph[other][layer]
                if len(links)>limit:
                    keep=set(self._select(self.vectors[other],[(distance(self.vectors[other],self.vectors[n]),n) for n in links],limit))
                    for removed in links-keep: self.graph[removed][layer].discard(other)
                    self.graph[other][layer]=keep
            if candidates: entry=candidates[0][1]
        if level>max_level: self.entry=id

    def search(self,query,k=10,ef=None):
        if k<0: raise ValueError('k must be nonnegative')
        if not self.entry or not k: return []
        query=normalize(query); entry=self.entry
        for layer in range(self.levels[entry],0,-1): entry=self._greedy(query,entry,layer)
        candidates=self._layer_search(query,[entry],max(k,ef or self.ef_search),0)
        return [VectorHit(id,1-d) for d,id in candidates][:k]
