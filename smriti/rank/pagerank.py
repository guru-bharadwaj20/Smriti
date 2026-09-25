"""Sparse confidence-weighted personalized PageRank."""
EDGE_WEIGHTS={"calls":1.0,"imports":0.5,"contains":0.3,"defines":0.3,"inherits":0.7,"tests":1.0,"config":0.6}
def edge_weight(kind,confidence=1.0):
    if not 0<=confidence<=1: raise ValueError("confidence outside [0,1]")
    return EDGE_WEIGHTS.get(kind,0.1)*confidence

def adjacency(nodes,edges):
    result={id:{} for id in nodes}
    for edge in edges:
        source,target,kind,*rest=edge
        confidence=rest[0] if rest else 1.0
        if source not in result or target not in result: continue
        weight=edge_weight(kind,confidence)
        if weight>0: result[source][target]=result[source].get(target,0)+weight
    return result

def transitions(graph):
    return {node:{other:weight/sum(links.values()) for other,weight in links.items()} if links else {} for node,links in graph.items()}
