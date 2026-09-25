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

def restart_distribution(nodes,seeds):
    nodes=list(nodes)
    values={id:max(0.0,seeds.get(id,0.0)) for id in nodes}
    total=sum(values.values())
    return {id:value/total if total else 1/len(nodes) for id,value in values.items()}

def personalized_pagerank(graph,seeds,damping=0.85,tolerance=1e-10,max_iterations=200):
    if not graph: return {}
    restart=restart_distribution(graph,seeds); scores=restart.copy(); matrix=transitions(graph)
    for _ in range(max_iterations):
        dangling=sum(scores[id] for id,links in matrix.items() if not links)
        updated={id:(1-damping)*restart[id]+damping*dangling*restart[id] for id in graph}
        for source,links in matrix.items():
            for target,weight in links.items(): updated[target]+=damping*scores[source]*weight
        delta=sum(abs(updated[id]-scores[id]) for id in graph)
        scores=updated
        if delta<tolerance: break
    return dict(sorted(scores.items(),key=lambda item:(-item[1],item[0])))
