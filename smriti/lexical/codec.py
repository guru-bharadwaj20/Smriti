"""Lossless delta and variable-byte posting codecs."""
def deltas(ids):
    result=[]
    previous=0
    for value in ids:
        if value < previous or value < 0: raise ValueError("posting IDs must be sorted nonnegative")
        result.append(value-previous)
        previous=value
    return result

def encode(values):
    out=bytearray()
    for value in values:
        if value < 0: raise ValueError("unsigned integers required")
        while value >= 128:
            out.append(value & 127)
            value >>= 7
        out.append(value | 128)
    return bytes(out)
