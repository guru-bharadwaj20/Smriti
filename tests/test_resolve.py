from smriti.parse import parse_file
from smriti.resolve import Resolver
from smriti.models import Edge


def test_scope_parent_links():
    result = parse_file("a.py", "def outer():\n    def inner():\n        pass\n    inner()\n")
    resolver = Resolver([result])
    assert resolver.parents[result.symbols[2].id] == result.symbols[1].id
    assert resolver.resolve_name("inner", result.symbols[1].id) == result.symbols[2].id


def test_local_alias_and_parameter_shadowing():
    result = parse_file("a.py", "def outer(callback):\n    def inner():\n        pass\n    alias = inner\n    alias()\n    callback()\n")
    resolver = Resolver([result])
    outer, inner = result.symbols[1:]
    assert resolver.resolve_name("alias", outer.id) == inner.id
    assert resolver.resolve_name("callback", outer.id) is None
