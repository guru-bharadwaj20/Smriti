"""Deterministic query normalization, fusion, and graph propagation."""
import unicodedata
def normalize_query(query):
    return ' '.join(unicodedata.normalize('NFKC',query).split()).casefold()

def lexical_candidates(index,query,k=50):
    return index.search(normalize_query(query),k)

def vector_candidates(index,embed,query,k=50):
    return index.search(embed(normalize_query(query)),k)

def reciprocal_rank_fusion(rankings,weights=None,constant=60):
    if constant<=0: raise ValueError('positive fusion constant required')
    weights=weights or [1.0]*len(rankings)
    if len(weights)!=len(rankings) or any(w<0 for w in weights): raise ValueError('invalid fusion weights')
    scores={}
    for ranking,weight in zip(rankings,weights):
        seen=set()
        for position,hit in enumerate(ranking,1):
            id=hit if isinstance(hit,str) else hit.id
            if id in seen: continue
            seen.add(id); scores[id]=scores.get(id,0)+weight/(constant+position)
    return dict(sorted(scores.items(),key=lambda item:(-item[1],item[0])))

def expand_callers(seeds,edges):
    selected=set(seeds)
    for source,target,kind,*_ in edges:
        if kind=='calls' and target in seeds: selected.add(source)
    return selected

def expand_associations(seeds,edges):
    selected=set(seeds)
    for source,target,kind,*_ in edges:
        if kind in {'tests','config'} and (source in seeds or target in seeds): selected.update([source,target])
    return selected

class RankingCache:
    def __init__(self): self.values={}; self.version=None
    def get(self,version,query): return self.values.get((version,normalize_query(query)))
    def put(self,version,query,scores): self.values[(version,normalize_query(query))]=dict(scores)

    def invalidate(self,version):
        self.values={key:value for key,value in self.values.items() if key[0]==version}; self.version=version

def explain_candidates(scores,lexical=(),vector=(),graph_scores=None):
    lexical={hit if isinstance(hit,str) else hit.id for hit in lexical}
    vector={hit if isinstance(hit,str) else hit.id for hit in vector}
    return {id:{'score':score,'lexical':id in lexical,'vector':id in vector,'graph_score':(graph_scores or {}).get(id,0)} for id,score in scores.items()}
