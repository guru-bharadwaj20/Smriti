from smriti.parse import SourceParser, parse_file


def test_tree_sitter_lifecycle():
    parser = SourceParser()
    result = parser.parse("a.py", "def f():\n    return 1\n")
    assert result.tree.root_node.type == "module"
    assert not result.tree.root_node.has_error
    assert parser.parse("b.py", "x = 1").tree.root_node.type == "module"
