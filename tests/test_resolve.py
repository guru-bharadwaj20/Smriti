from smriti.parse import parse_file
from smriti.resolve import Resolver
from smriti.models import Edge


def test_scope_parent_links():
    result = parse_file("a.py", "def outer():\n    def inner():\n        pass\n    inner()\n")
    resolver = Resolver([result])
    assert resolver.parents[result.symbols[2].id] == result.symbols[1].id
    assert resolver.resolve_name("inner", result.symbols[1].id) == result.symbols[2].id
