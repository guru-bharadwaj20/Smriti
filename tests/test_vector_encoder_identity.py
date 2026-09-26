from smriti.vector.embedding import encoder_identity


def test_encoder_cache_identity_changes_with_tokenizer_or_weights(tmp_path):
    model = tmp_path / 'model.onnx'
    tokenizer = tmp_path / 'tokenizer.json'
    model.write_bytes(b'weights')
    tokenizer.write_bytes(b'tokenizer')
    first = encoder_identity(model, tokenizer)
    assert first == encoder_identity(model, tokenizer)
    tokenizer.write_bytes(b'changed tokenizer')
    assert first != encoder_identity(model, tokenizer)
    tokenizer.write_bytes(b'tokenizer')
    model.write_bytes(b'changed weights')
    assert first != encoder_identity(model, tokenizer)
