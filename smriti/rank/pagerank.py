"""Sparse confidence-weighted personalized PageRank."""
EDGE_WEIGHTS={"calls":1.0,"imports":0.5,"contains":0.3,"defines":0.3,"inherits":0.7,"tests":1.0,"config":0.6}
def edge_weight(kind,confidence=1.0):
    return EDGE_WEIGHTS.get(kind,0.1)
