"""Lossless delta and variable-byte posting codecs."""

from collections.abc import Iterable


def deltas(ids: Iterable[int]) -> list[int]:
    result = []
    previous = 0
    for value in ids:
        if value < previous or value < 0:
            raise ValueError('posting IDs must be sorted nonnegative')
        result.append(value - previous)
        previous = value
    return result


def encode(values: Iterable[int]) -> bytes:
    out = bytearray()
    for value in values:
        if value < 0:
            raise ValueError('unsigned integers required')
        while value >= 128:
            out.append(value & 127)
            value >>= 7
        out.append(value | 128)
    return bytes(out)


def decode(data: bytes) -> list[int]:
    result = []
    value = shift = 0
    for byte in data:
        value |= (byte & 127) << shift
        if byte & 128:
            result.append(value)
            value = shift = 0
        else:
            shift += 7
    if shift:
        raise ValueError('truncated variable-byte stream')
    return result


def posting_ids(data: bytes) -> list[int]:
    value = 0
    result = []
    for delta in decode(data):
        value += delta
        result.append(value)
    return result
