from smriti.parse import SourceParser, parse_file


def test_tree_sitter_lifecycle():
    parser = SourceParser()
    result = parser.parse("a.py", "def f():\n    return 1\n")
    assert result.tree.root_node.type == "module"
    assert not result.tree.root_node.has_error
    assert parser.parse("b.py", "x = 1").tree.root_node.type == "module"


def test_module_scope():
    result = parse_file("pkg/__init__.py", "x=1")
    assert result.symbols[0].kind == "module"
    assert result.symbols[0].qualname == "pkg"
    assert result.symbols[0].body == "x=1"


def test_class_definitions():
    result = parse_file("a.py", "class A:\n    class B:\n        pass\n")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert [s.qualname for s in classes] == ["a.A", "a.A.B"]
    assert classes[1].parent_id == classes[0].id


def test_functions_and_methods():
    result = parse_file("a.py", "def f():\n    pass\nclass A:\n    async def m(self):\n        pass\n")
    assert [(s.name, s.kind) for s in result.symbols] == [("a", "module"), ("f", "function"), ("A", "class"), ("m", "method")]
    assert len({s.id for s in result.symbols}) == 4


def test_signatures_and_docstrings():
    result = parse_file("a.py", 'def f(x: int = 1) -> str:\n    "description"\n    return str(x)\n')
    symbol = result.symbols[1]
    assert symbol.signature == "def f(x: int = 1) -> str"
    assert symbol.docstring == "description"


def test_source_offsets():
    from smriti.parse import source_slice
    result = parse_file("a.py", "# header\ndef f():\n    return 1\n")
    symbol = result.symbols[1]
    assert (symbol.start_line, symbol.end_line) == (2, 3)
    assert source_slice(result, symbol).decode() == symbol.body


def test_import_declarations():
    result = parse_file("pkg/a.py", "import os.path as p\nfrom .helpers import work as run\n")
    assert result.imports[0]["alias"] == "p"
    assert result.imports[0]["module"] == "os.path"
    assert result.imports[1]["name"] == "work"
    assert result.imports[1]["level"] == 1


def test_call_candidates():
    result = parse_file("a.py", "def f():\n    obj.run(helper())\n")
    assert [call["name"] for call in result.calls] == ["obj.run", "helper"]
    assert all(call["scope"] == result.symbols[1].id for call in result.calls)


def test_inheritance_declarations():
    result = parse_file("a.py", "class A(Base, pkg.Other):\n    pass\n")
    assert [base["name"] for base in result.inheritance] == ["Base", "pkg.Other"]
    assert all(base["class"] == result.symbols[1].id for base in result.inheritance)


def test_nested_and_comprehension_scopes():
    result = parse_file("a.py", "def outer():\n    def inner():\n        return [x for x in range(3)]\n    return inner()\n")
    assert result.symbols[2].parent_id == result.symbols[1].id
    assert result.symbols[2].qualname == "a.outer.inner"
    assert result.comprehensions[0]["parent"] == result.symbols[2].id


def test_invalid_syntax_diagnostics():
    result = parse_file("a.py", "def broken(:\n    x =\n")
    assert result.tree.root_node.has_error
    assert result.diagnostics
    assert all(d["line"] >= 1 for d in result.diagnostics)


def test_incremental_parse_matches_fresh():
    parser = SourceParser()
    old = parser.parse("a.py", "def f():\n    return 1\n")
    new = parser.parse("a.py", "# comment\ndef f():\n    return 22\n")
    fresh = SourceParser().parse("a.py", new.source)
    assert new.symbols == fresh.symbols
    assert old.symbols[1].start_line == 1
    assert new.symbols[1].start_line == 2


def test_unicode_and_crlf_offsets():
    from smriti.parse import source_slice, byte_point
    source = "# café\r\ndef π():\r\n    return '你好'\r\n"
    result = parse_file("unicode.py", source)
    symbol = result.symbols[1]
    assert symbol.name == "π"
    assert source_slice(result, symbol).decode("utf-8") == symbol.body
    assert byte_point(result.source, symbol.start_byte) == (1, 0)
    parser = SourceParser()
    parser.parse("unicode.py", source)
    edited = parser.parse("unicode.py", source.replace("你好", "再见"))
    assert edited.symbols == parse_file("unicode.py", edited.source).symbols


def test_chunks_follow_symbol_boundaries():
    from smriti.parse import symbol_chunks
    result = parse_file("a.py", "def a():\n    pass\ndef b():\n    pass\n")
    chunks = symbol_chunks(result)
    assert len(chunks) == 2
    assert chunks[0][1].startswith(b"def a")
    assert chunks[1][1].startswith(b"def b")
