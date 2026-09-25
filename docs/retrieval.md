# Retrieval

HNSW uses normalized cosine distance, a fixed seed, M >= 2, and ef_construction >= M. Layer zero permits 2M neighbors; upper layers permit M. Construction explores ef_construction candidates per layer.
