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
    return name_text(symbol)+symbol.signature+'\n'+((symbol.docstring+'\n') if symbol.docstring else '')+f'# ... lines {symbol.start_line}-{getattr(symbol,"end_line",symbol.start_line)} omitted\n'

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

def greedy(groups,budget):
    chosen=[options[0] for options in groups]; used=0
    while True:
        upgrades=[]
        for i,options in enumerate(groups):
            current=chosen[i]
            for option in options:
                extra=option.cost-current.cost; gain=option.value-current.value
                if gain>0 and extra>=0 and used+extra<=budget:
                    upgrades.append((gain/max(extra,1),gain,-extra,-i,option))
        if not upgrades: return chosen
        *_,negative_i,option=max(upgrades,key=lambda u:u[:4]); i=-negative_i
        used+=option.cost-chosen[i].cost; chosen[i]=option

def add_parent_context(groups,symbols,counter):
    by_id={symbol.id:symbol for symbol in symbols}
    result=[]
    for symbol,options in zip(symbols,groups):
        parent=by_id.get(getattr(symbol,'parent_id',None))
        if parent and parent.kind=='class' and symbol.kind in {'method','function'}:
            header=signature_text(parent)
            options=[Representation(o.id,o.level,header+o.text,counter.count(header+o.text),o.value) if o.level!='omit' else o for o in options]
        result.append(options)
    return result

def deduplicate_bodies(chosen,symbols):
    by_id={s.id:s for s in symbols}; full={o.id for o in chosen if o.level=='body'}
    result=[]
    for option in chosen:
        symbol=by_id[option.id]; parent=getattr(symbol,'parent_id',None)
        covered=False
        while parent and parent in by_id:
            if parent in full: covered=True; break
            parent=getattr(by_id[parent],'parent_id',None)
        if not covered and option.level!='omit': result.append(option)
    return result

def covered_symbols(chosen,symbols):
    by_id={s.id:s for s in symbols}; full={o.id for o in chosen if o.level=='body'}
    covered={o.id for o in chosen if o.level!='omit'}
    for symbol in symbols:
        parent=getattr(symbol,'parent_id',None)
        while parent and parent in by_id:
            if parent in full: covered.add(symbol.id); break
            parent=getattr(by_id[parent],'parent_id',None)
    return covered

def stable_order(chosen,symbols):
    by_id={s.id:s for s in symbols}
    return sorted(chosen,key=lambda o:(by_id[o.id].path,by_id[o.id].start_line,o.id))

@dataclass(frozen=True)
class PackedContext:
    text: str
    token_count: int
    items: list[Representation]
    tokenizer: str
    omitted_ids: list[str]
    covered_ids: list[str] = field(default_factory=list)

class ContextPacker:
    def __init__(self,counter=None):
        from .tokens import TokenCounter
        self.counter=counter or TokenCounter()
    def pack(self,symbols,scores,budget,memory_tokens=0,framing_tokens=0,bucket=1):
        symbols=list(symbols); available=available_budget(budget,memory_tokens,framing_tokens)
        groups=[representations(s,max(0,scores.get(s.id,0)),self.counter) for s in symbols]
        groups=add_parent_context(groups,symbols,self.counter)
        selected=knapsack(groups,available,bucket)
        selected=stable_order(deduplicate_bodies(selected,symbols),symbols)
        text=''.join(o.text for o in selected)
        count=self.counter.count(text)
        covered=covered_symbols(selected,symbols)
        return PackedContext(text,count,selected,self.counter.encoding_name,[s.id for s in symbols if s.id not in covered],sorted(covered))
