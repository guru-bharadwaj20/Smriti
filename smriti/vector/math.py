"""Dependency-free cosine distance and exhaustive nearest-neighbor oracle."""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float

def normalize(vector):
    values=tuple(float(x) for x in vector)
    if not values or not all(math.isfinite(x) for x in values): raise ValueError("finite nonempty vector required")
    norm=math.sqrt(sum(x*x for x in values))
    if not norm: raise ValueError("zero vector has no cosine direction")
    return tuple(x/norm for x in values)

def distance(a,b):
    if len(a)!=len(b): raise ValueError("dimension mismatch")
    return max(0.0,min(2.0,1-sum(x*y for x,y in zip(a,b))))
