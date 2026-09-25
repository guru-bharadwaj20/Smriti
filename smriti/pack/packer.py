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

def body_text(symbol):
    return name_text(symbol)+'```python\n'+symbol.body+'\n```\n'

def representations(symbol,score,counter):
    texts={'name':name_text(symbol),'signature':signature_text(symbol),'body':body_text(symbol)}
    return [omitted(symbol)]+[Representation(symbol.id,level,text,counter.count(text),score) for level,text in texts.items()]

def available_budget(budget,memory_tokens=0,framing_tokens=0):
    if min(budget,memory_tokens,framing_tokens)<0: raise ValueError('budgets must be nonnegative')
    return max(0,budget-memory_tokens-framing_tokens)
