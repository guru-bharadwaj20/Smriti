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
