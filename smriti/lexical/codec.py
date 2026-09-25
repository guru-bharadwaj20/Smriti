"""Lossless delta and variable-byte posting codecs."""
def deltas(ids):
    result=[]
    previous=0
    for value in ids:
        if value < previous or value < 0: raise ValueError("posting IDs must be sorted nonnegative")
        result.append(value-previous)
        previous=value
    return result
