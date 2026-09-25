"""Compare custom HNSW and hnswlib with a common seeded exact oracle."""
from pathlib import Path
import hashlib,json,os,platform,random,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

def run():
    import numpy as np
    build_metadata=None
    local=Path(__file__).resolve().parents[2]/'.smriti'/'deps'
    if (local/'reference_build.json').exists():
        build=json.loads((local/'reference_build.json').read_text())
        binary=Path(build['output'])
        if not binary.is_relative_to(local) or hashlib.sha256(binary.read_bytes()).hexdigest()!=build['binary_sha256']: raise ValueError('local reference checksum mismatch')
        sys.path.insert(0,str(local))
        dll_directory=os.add_dll_directory(str(Path(build['compiler']).parent))
        build_metadata={key:build[key] for key in ['source','headers','compiler_version','binary_sha256']}
    import hnswlib
    from smriti.vector.hnsw import HNSWIndex
    from smriti.vector.math import exact_search,normalize
    rng=random.Random(81)
    vectors={str(i):normalize([rng.gauss(0,1) for _ in range(16)]) for i in range(400)}
    queries=[normalize([rng.gauss(0,1) for _ in range(16)]) for _ in range(100)]
    custom=HNSWIndex(m=12,ef_construction=100,ef_search=100,seed=81)
    start=time.perf_counter()
    for id,vector in vectors.items(): custom.add(id,vector)
    custom_build=time.perf_counter()-start
    reference=hnswlib.Index(space='cosine',dim=16)
    reference.init_index(max_elements=400,ef_construction=100,M=12,random_seed=81)
    start=time.perf_counter(); reference.add_items(np.asarray(list(vectors.values()),dtype=np.float32),np.arange(400),num_threads=1)
    reference_build=time.perf_counter()-start
    reference.set_ef(100); reference.set_num_threads(1)
    metrics={}
    for name,search in [('custom',lambda q:[h.id for h in custom.search(q,10)]),('hnswlib',lambda q:[str(i) for i in reference.knn_query(np.asarray([q],dtype=np.float32),k=10)[0][0]])]:
        latencies=[]; recalls=[]
        for query in queries:
            truth={h.id for h in exact_search(vectors,query,10)}
            start=time.perf_counter(); found=search(query); latencies.append(time.perf_counter()-start)
            recalls.append(len(truth&set(found))/10)
        metrics[name]={'recall_at_10':sum(recalls)/len(recalls),'query_ms_p50':sorted(latencies)[50]*1000,'query_ms_p95':sorted(latencies)[95]*1000,'queries_per_second':len(queries)/sum(latencies)}
    return {'dataset':'synthetic-v1','seed':81,'vectors':400,'dimensions':16,'queries':100,'cpu':platform.processor(),'os':platform.platform(),'python':platform.python_version(),'config':{'M':12,'efConstruction':100,'efSearch':100,'threads':1},'reference_build':build_metadata,'construction_seconds':{'custom':custom_build,'hnswlib':reference_build},'metrics':metrics,'limitation':'Synthetic ANN comparison. Different implementations may build different graphs; this does not measure semantic code retrieval.'}

if __name__=='__main__':
    result=run()
    path=Path(__file__).with_name('hnsw_reference.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    if '--commit' in sys.argv:
        import subprocess
        subprocess.run([sys.executable,'scripts/task_commit.py','P06.25','compare custom HNSW against hnswlib on CPU','--evidence','bench/vector/hnsw_reference.py; bench/vector/hnsw_reference.json; real exact-oracle recall and throughput','--files','bench/vector/hnsw_reference.py','bench/vector/hnsw_reference.json','bench/vector/build_reference.py'],check=True)
    else: print(json.dumps(result,indent=2))
