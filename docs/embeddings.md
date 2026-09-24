# CPU embeddings

Selected model: [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41), Apache-2.0 according to the publisher model card. Model dimensions: 384. Mean pooling uses the attention mask, followed by L2 normalization. Input is limited to 256 word pieces, matching the published model configuration. This is a general sentence encoder; code retrieval quality requires held-out evaluation. Use ONNX Runtime CPUExecutionProvider only.

Primary documentation: [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [ONNX Runtime Python API](https://onnxruntime.ai/docs/api/python/api_summary.html).
