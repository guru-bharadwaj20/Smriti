"""Budgeted symbol representations with multiple-choice knapsack selection."""
from dataclasses import dataclass,field

@dataclass(frozen=True)
class Representation:
    id: str
    level: str
    text: str
    cost: int
    value: float

def omitted(symbol):
    return Representation(symbol.id,'omit','',0,0.0)

def name_text(symbol):
    return f'{symbol.path}:{symbol.start_line} {symbol.qualname}\n'

def signature_text(symbol):
    return name_text(symbol)+symbol.signature+'\n'+((symbol.docstring+'\n') if symbol.docstring else '')
