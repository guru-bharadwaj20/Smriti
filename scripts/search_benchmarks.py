"""Measure component performance on deterministic synthetic fixtures."""
from pathlib import Path
import json,platform,random,subprocess,sys,time,tracemalloc,tempfile
sys.path.insert(0,str(Path.cwd()))

def commit(task,message,files):
    subprocess.run([sys.executable,'scripts/task_commit.py',task,message,'--evidence','; '.join(files)+'; measured CPU synthetic run','--files',*files],check=True)

def environment():
    return {'python':platform.python_version(),'os':platform.platform(),'cpu':platform.processor(),'seed':81,'dataset':'synthetic-v1','note':'Component smoke benchmark; not SWE-bench or semantic retrieval quality.'}

def lexical():
    from smriti.lexical.index import BM25Index
    index=BM25Index()
    for i in range(200): index.add(str(i),{'signature':f'def load_user_{i}():','docstring':'Load user settings','body':f'return user_config_{i}'})
    samples=[]
    for i in range(100):
        start=time.perf_counter(); index.search(f'user config {i}',10); samples.append((time.perf_counter()-start)*1000)
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'index.json'; index.save(path); storage=path.stat().st_size
    return environment()|{'symbols':200,'queries':100,'query_ms_p50':sorted(samples)[50],'query_ms_p95':sorted(samples)[95],'storage_bytes':storage}

def vector():
    from smriti.vector.hnsw import HNSWIndex
    from smriti.vector.math import exact_search
    r=random.Random(81); vectors={str(i):[r.gauss(0,1) for _ in range(16)] for i in range(400)}
    tracemalloc.start(); index=HNSWIndex(m=12,ef_search=100)
    start=time.perf_counter()
    for id,v in vectors.items(): index.add(id,v)
    construction=time.perf_counter()-start
    samples=[]; recalls=[]
    for query in list(vectors.values())[:100]:
        start=time.perf_counter(); found=index.search(query,10); samples.append((time.perf_counter()-start)*1000)
        truth={h.id for h in exact_search(vectors,query,10)}; recalls.append(len(truth & {h.id for h in found})/10)
    _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop(); index.validate()
    return environment()|{'vectors':400,'dimensions':16,'queries':100,'m':12,'ef_search':100,'construction_seconds':construction,'query_ms_p50':sorted(samples)[50],'query_ms_p95':sorted(samples)[95],'peak_python_bytes':peak,'recall_at_10':sum(recalls)/len(recalls)}

def packing():
    from smriti.pack.packer import Representation,knapsack,greedy
    r=random.Random(81); groups=[[Representation(str(i),'omit','',0,0)]+[Representation(str(i),str(j),'',r.randrange(10,150),r.random()*10) for j in range(3)] for i in range(40)]
    timings=[]; ratios=[]
    for budget in [256,512,1024,2048]:
        start=time.perf_counter(); optimal=knapsack(groups,budget); elapsed=(time.perf_counter()-start)*1000
        baseline=greedy(groups,budget)
        value=sum(x.value for x in optimal); greedy_value=sum(x.value for x in baseline)
        timings.append({'budget':budget,'dp_ms':elapsed,'dp_value':value,'greedy_value':greedy_value,'greedy_to_dp':greedy_value/value,'used_cost':sum(x.cost for x in optimal)})
    return environment()|{'groups':40,'options_per_group':4,'measurements':timings,'note':'Independent additive option values; constrained method packing excluded.'}

if __name__=='__main__':
    command=sys.argv[1]
    if command=='lexical': result=lexical(); task='P05.21'; destination='bench/lexical/results.json'
    elif command=='vector': result=vector(); task='P06.26'; destination='bench/vector/results.json'
    elif command=='packing': result=packing(); task='P08.21'; destination='bench/packing/results.json'
    else: raise SystemExit('choose lexical, vector, or packing')
    path=Path(destination); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(result,indent=2)+'\n')
    runner=Path(destination).with_name('run.py')
    runner.write_text('"""Reproduce the recorded deterministic component benchmark."""\nimport runpy,sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[2]))\nnamespace=runpy.run_path(str(Path(__file__).resolve().parents[2]/"scripts/search_benchmarks.py"))\nimport json\nprint(json.dumps(namespace["'+command+'"](),indent=2))\n')
    commit(task,'measure '+command+' CPU synthetic performance',[destination,str(runner).replace('\\','/'),'scripts/search_benchmarks.py'])
