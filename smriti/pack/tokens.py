"""Explicit target tokenizer; byte fallback is conservative and clearly labeled."""


class TokenCounter:
    def __init__(self, encoding: str = 'cl100k_base') -> None:
        import tiktoken

        self.encoding_name = encoding
        self.encoding = tiktoken.get_encoding(encoding)

    def count(self, text: str) -> int:
        return len(self.encoding.encode(text, disallowed_special=()))


class ByteCounter:
    encoding_name = 'utf8-byte-upper-bound'

    def count(self, text: str) -> int:
        return len(text.encode('utf-8'))
