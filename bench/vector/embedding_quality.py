"""Evaluate pinned eight-bit encoder agreement on explicit smoke fixtures."""
import json,platform,time
from pathlib import Path
from smriti.vector.download import download_model
from smriti.vector.embedding import ONNXEmbedder
from smriti.vector.math import exact_search

TEXTS=['def load_user(id): return db.get(id)','def save_user(user): db.put(user)','def delete_user(id): db.delete(id)','def hash_password(value): return sha256(value)','def validate_token(token): return decode(token)','def parse_config(path): return json.load(path)','def read_file(path): return path.read_text()','def write_file(path,data): path.write_text(data)','def run_tests(): return pytest.main()','def start_server(port): app.listen(port)','def stop_server(): app.close()','def fetch_url(url): return requests.get(url)']
QUERIES=['load a database user','write settings file','authenticate password','start HTTP service','execute tests','download a web resource']

def evaluate():
    fp,tokenizer=download_model('.smriti/models'); quant,_=download_model('.smriti/models',quantized=True)
    a=ONNXEmbedder(fp,tokenizer); b=ONNXEmbedder(quant,tokenizer)
    start=time.perf_counter(); av=a.embed(TEXTS); at=time.perf_counter()-start
    start=time.perf_counter(); bv=b.embed(TEXTS); bt=time.perf_counter()-start
    agreement=[sum(x*y for x,y in zip(v,w)) for v,w in zip(av,bv)]
    aq=a.embed(QUERIES); bq=b.embed(QUERIES); overlap=[]
    for q,r in zip(aq,bq):
        gold={h.id for h in exact_search({str(i):v for i,v in enumerate(av)},q,5)}
        actual={h.id for h in exact_search({str(i):v for i,v in enumerate(bv)},r,5)}
        overlap.append(len(gold&actual)/5)
    return {'hardware':platform.processor(),'os':platform.platform(),'python':platform.python_version(),'texts':TEXTS,'queries':QUERIES,'mean_cosine_fp32_uint8':sum(agreement)/len(agreement),'minimum_cosine_fp32_uint8':min(agreement),'mean_top5_overlap':sum(overlap)/len(overlap),'fp32_batch_seconds':at,'uint8_batch_seconds':bt,'note':'Small code smoke fixture; embedding/rank preservation only, not held-out SWE-bench retrieval quality or evidence of int8 speedup.'}

if __name__=='__main__': print(json.dumps(evaluate(),indent=2))
