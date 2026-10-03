"""Tune fusion weights only on explicitly partitioned synthetic validation ranks."""
from pathlib import Path
import itertools,json,sys
sys.path.insert(0,str(Path.cwd()))

FIXTURE={
    'kind':'synthetic rank fixture, not SWE-bench',
    'validation':[
        {'lexical':['v1','v2','v3'],'vector':['v2','v1','v3'],'gold':['v1']},
        {'lexical':['v4','v5','v6'],'vector':['v5','v4','v6'],'gold':['v4']},
        {'lexical':['v7','v8','v9'],'vector':['v8','v7','v9'],'gold':['v8']},
    ],
    'held_out':[
        {'lexical':['t1','t2','t3'],'vector':['t2','t1','t3'],'gold':['t1']},
        {'lexical':['t4','t5','t6'],'vector':['t5','t4','t6'],'gold':['t5']},
    ],
}

def mrr(cases,weights):
    from smriti.rank.hybrid import reciprocal_rank_fusion
    values=[]
    for case in cases:
        ranked=list(reciprocal_rank_fusion([case['lexical'],case['vector']],weights=weights))
        values.append(max([1/(ranked.index(id)+1) for id in case['gold'] if id in ranked],default=0))
    return sum(values)/len(values)

if __name__=='__main__':
    choices=list(itertools.product([0.25,0.5,1.0,2.0],repeat=2))
    weights=max(choices,key=lambda w:(mrr(FIXTURE['validation'],w),-sum(w),w))
    output={'fixture':FIXTURE,'selected_weights':weights,'validation_mrr':mrr(FIXTURE['validation'],weights),'held_out_mrr':mrr(FIXTURE['held_out'],weights),'limitation':'Synthetic fusion implementation check; do not adopt these weights for real retrieval without representative validation.'}
    Path('bench/fusion').mkdir(parents=True,exist_ok=True)
    Path('bench/fusion/validation.json').write_text(json.dumps(output,indent=2)+'\n')
