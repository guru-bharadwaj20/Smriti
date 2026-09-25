"""Explicit local ONNX CPU encoder with attention-mask mean pooling."""
from pathlib import Path
from .math import normalize

class ONNXEmbedder:
    def __init__(self,model_path,tokenizer_path,threads=1,version=None):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        import hashlib
        options=ort.SessionOptions(); options.intra_op_num_threads=threads
        self.session=ort.InferenceSession(str(model_path),sess_options=options,providers=['CPUExecutionProvider'])
        self.tokenizer=Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=256); self.tokenizer.enable_padding()
        self.version=version or hashlib.file_digest(Path(model_path).open('rb'),'sha256').hexdigest()
    def embed(self,texts):
        import numpy as np
        if not texts: return []
        encoded=self.tokenizer.encode_batch(list(texts))
        values={'input_ids':np.asarray([x.ids for x in encoded],dtype=np.int64),'attention_mask':np.asarray([x.attention_mask for x in encoded],dtype=np.int64),'token_type_ids':np.asarray([x.type_ids for x in encoded],dtype=np.int64)}
        inputs={node.name:values[node.name] for node in self.session.get_inputs()}
        tokens=self.session.run(None,inputs)[0]
        mask=values['attention_mask'][...,None]
        pooled=(tokens*mask).sum(axis=1)/np.maximum(mask.sum(axis=1),1)
        return [normalize(vector) for vector in pooled]
    def __call__(self,text): return self.embed([text])[0]
