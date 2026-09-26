from smriti.lexical.tokenizer import tokenize


def test_snake_identifiers():
    assert tokenize('__load_user_id__') == ['load', 'user', 'id']
