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


def test_enclosing_scope_resolution():
    result = parse_file("a.py", "def outer():\n    def helper():\n        pass\n    def inner():\n        helper()\n")
    resolver = Resolver([result])
    assert resolver.resolve_name("helper", result.symbols[3].id) == result.symbols[2].id


def test_nonlocal_declaration_uses_enclosing_scope():
    result = parse_file("a.py", "def outer():\n    def helper():\n        pass\n    def inner():\n        nonlocal helper\n        helper()\n")
    resolver = Resolver([result])
    assert resolver.resolve_name("helper", result.symbols[3].id) == result.symbols[2].id


def test_module_level_names_and_recursion():
    result = parse_file("a.py", "def helper():\n    helper()\ndef worker():\n    helper()\n")
    resolver = Resolver([result])
    assert resolver.resolve_name("helper", result.symbols[2].id) == result.symbols[1].id
    assert resolver.resolve_name("helper", result.symbols[1].id) == result.symbols[1].id
    assert resolver.resolve_name("a.helper", result.symbols[0].id) == result.symbols[1].id


def test_aliased_imports():
    helper = parse_file("helpers.py", "def work():\n    pass\n")
    client = parse_file("client.py", "from helpers import work as run\nimport helpers as h\ndef main():\n    run()\n    h.work()\n")
    resolver = Resolver([helper, client])
    assert resolver.resolve_name("run", client.symbols[1].id) == helper.symbols[1].id
    assert resolver.resolve_name("h.work", client.symbols[1].id) == helper.symbols[1].id


def test_relative_imports():
    helper = parse_file("pkg/helpers.py", "def work():\n    pass\n")
    client = parse_file("pkg/client.py", "from .helpers import work\ndef main():\n    work()\n")
    resolver = Resolver([helper, client])
    assert resolver.resolve_name("work", client.symbols[1].id) == helper.symbols[1].id


def test_reexports_and_cycles_are_conservative():
    original = parse_file("impl.py", "def work():\n    pass\n")
    export = parse_file("api.py", "from impl import work\n")
    client = parse_file("client.py", "from api import work as run\ndef main():\n    run()\n")
    resolver = Resolver([original, export, client])
    assert resolver.resolve_name("run", client.symbols[1].id) == original.symbols[1].id
    a = parse_file("a.py", "from b import unknown\n")
    b = parse_file("b.py", "from a import unknown\n")
    assert Resolver([a, b]).resolve_name("unknown", a.symbols[0].id) is None
