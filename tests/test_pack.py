from smriti.pack.packer import Representation,knapsack
def test_bucket_budget():
    groups=[[Representation(str(i),'omit','',0,0),Representation(str(i),'body','x',3,5)] for i in range(3)]
    chosen=knapsack(groups,7,bucket=2)
    assert sum(x.cost for x in chosen)<=7

def test_oversized_degrades():
    options=[Representation('a','omit','',0,0),Representation('a','name','f',1,1),Representation('a','body','long',100,5)]
    assert knapsack([options],2)[0].level=='name'

def test_exhaustive_oracle():
    import itertools,random
    r=random.Random(55)
    for _ in range(50):
        groups=[[Representation(str(i),'omit','',0,0)]+[Representation(str(i),str(j),'',r.randrange(1,10),r.random()*10) for j in range(3)] for i in range(4)]
        budget=r.randrange(5,25)
        gold=max(sum(o.value for o in choice) for choice in itertools.product(*groups) if sum(o.cost for o in choice)<=budget)
        assert abs(sum(o.value for o in knapsack(groups,budget))-gold)<1e-9

def test_final_recount_enforces_budget():
    from smriti.pack.packer import ContextPacker
    from types import SimpleNamespace as S
    class Counter:
        encoding_name='adversarial-test'
        def count(self,text): return len(text)+(10000 if 'first' in text and 'second' in text else 0)
    symbols=[S(id=id,path='a.py',start_line=i,end_line=i+1,qualname=id,signature=f'def {id}():',docstring='',body=f'def {id}(): pass',parent_id=None,kind='function') for i,id in enumerate(['first','second'],1)]
    result=ContextPacker(Counter()).pack(symbols,{'first':1,'second':1},500)
    assert result.token_count<=500
    assert len(result.items)==1
