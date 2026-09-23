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
