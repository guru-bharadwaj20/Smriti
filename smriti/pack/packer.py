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
    return [omitted(symbol)]+[Representation(symbol.id,level,text,counter.count(text),score*{"name":0.15,"signature":0.45,"body":1.0}[level]) for level,text in texts.items()]

def available_budget(budget,memory_tokens=0,framing_tokens=0):
    if min(budget,memory_tokens,framing_tokens)<0: raise ValueError('budgets must be nonnegative')
    return max(0,budget-memory_tokens-framing_tokens)

def knapsack(groups,budget,bucket=1):
    if budget<0 or bucket<1: raise ValueError('invalid budget or bucket')
    # Round option costs upward and budget downward: buckets never exceed budget.
    import math
    limit=budget//bucket; states={0:(0.0,None)}
    for options in groups:
        updated={}
        for cost,(value,chosen) in states.items():
            for option in options:
                total=cost+math.ceil(option.cost/bucket)
                if total>limit: continue
                candidate=(value+option.value,(option,chosen))
                if total not in updated or candidate[0]>updated[total][0]: updated[total]=candidate
        states=updated
    if not states: return []
    chain=max(states.items(),key=lambda item:(item[1][0],-item[0]))[1][1]
    result=[]
    while chain is not None:
        option,chain=chain; result.append(option)
    return list(reversed(result))
