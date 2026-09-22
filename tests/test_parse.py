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
