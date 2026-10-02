from smriti.models import Edge
from smriti.parse import parse_file
from smriti.resolve import Resolver


def test_scope_parent_links():
    result = parse_file('a.py', 'def outer():\n    def inner():\n        pass\n    inner()\n')
    resolver = Resolver([result])
    assert resolver.parents[result.symbols[2].id] == result.symbols[1].id
    assert resolver.resolve_name('inner', result.symbols[1].id) == result.symbols[2].id


def test_local_alias_and_parameter_shadowing():
    result = parse_file(
        'a.py',
        'def outer(callback):\n    def inner():\n        pass\n    alias = inner\n    alias()\n    callback()\n',
    )
    resolver = Resolver([result])
    outer, inner = result.symbols[1:]
    assert resolver.resolve_name('alias', outer.id) == inner.id
    assert resolver.resolve_name('callback', outer.id) is None


def test_enclosing_scope_resolution():
    result = parse_file(
        'a.py',
        'def outer():\n    def helper():\n        pass\n    def inner():\n        helper()\n',
    )
    resolver = Resolver([result])
    assert resolver.resolve_name('helper', result.symbols[3].id) == result.symbols[2].id


def test_nonlocal_declaration_uses_enclosing_scope():
    result = parse_file(
        'a.py',
        'def outer():\n    def helper():\n        pass\n    def inner():\n        nonlocal helper\n        helper()\n',
    )
    resolver = Resolver([result])
    assert resolver.resolve_name('helper', result.symbols[3].id) == result.symbols[2].id


def test_module_level_names_and_recursion():
    result = parse_file('a.py', 'def helper():\n    helper()\ndef worker():\n    helper()\n')
    resolver = Resolver([result])
    assert resolver.resolve_name('helper', result.symbols[2].id) == result.symbols[1].id
    assert resolver.resolve_name('helper', result.symbols[1].id) == result.symbols[1].id
    assert resolver.resolve_name('a.helper', result.symbols[0].id) == result.symbols[1].id


def test_aliased_imports():
    helper = parse_file('helpers.py', 'def work():\n    pass\n')
    client = parse_file(
        'client.py',
        'from helpers import work as run\nimport helpers as h\ndef main():\n    run()\n    h.work()\n',
    )
    resolver = Resolver([helper, client])
    assert resolver.resolve_name('run', client.symbols[1].id) == helper.symbols[1].id
    assert resolver.resolve_name('h.work', client.symbols[1].id) == helper.symbols[1].id


def test_relative_imports():
    helper = parse_file('pkg/helpers.py', 'def work():\n    pass\n')
    client = parse_file('pkg/client.py', 'from .helpers import work\ndef main():\n    work()\n')
    resolver = Resolver([helper, client])
    assert resolver.resolve_name('work', client.symbols[1].id) == helper.symbols[1].id


def test_reexports_and_cycles_are_conservative():
    original = parse_file('impl.py', 'def work():\n    pass\n')
    export = parse_file('api.py', 'from impl import work\n')
    client = parse_file('client.py', 'from api import work as run\ndef main():\n    run()\n')
    resolver = Resolver([original, export, client])
    assert resolver.resolve_name('run', client.symbols[1].id) == original.symbols[1].id
    a = parse_file('a.py', 'from b import unknown\n')
    b = parse_file('b.py', 'from a import unknown\n')
    assert Resolver([a, b]).resolve_name('unknown', a.symbols[0].id) is None


def test_builtin_external_and_dynamic_references_are_explicit():
    result = parse_file(
        'a.py', 'import missing as m\ndef f(callback):\n    len([])\n    m.run()\n    callback()\n'
    )
    edges = [edge for edge in Resolver([result]).resolve() if edge.kind == 'calls']
    assert {edge.target.split(':', 1)[0] for edge in edges} == {'builtin', 'external', 'dynamic'}
    assert all(edge.confidence < 1 for edge in edges)


def test_self_and_class_method_calls():
    result = parse_file(
        'a.py',
        'class A:\n    def helper(self):\n        pass\n    def run(self):\n        self.helper()\n',
    )
    resolver = Resolver([result])
    assert resolver.resolve_name('self.helper', result.symbols[3].id) == result.symbols[2].id


def test_c3_diamond_and_inconsistent_hierarchy():
    import pytest

    from smriti.resolve import c3_linearize

    bases = {'A': [], 'B': ['A'], 'C': ['A'], 'D': ['B', 'C']}
    assert c3_linearize('D', bases) == ['D', 'B', 'C', 'A']
    bases.update({'X': ['B', 'C'], 'Y': ['C', 'B'], 'Z': ['X', 'Y']})
    with pytest.raises(ValueError, match='Inconsistent'):
        c3_linearize('Z', bases)
    with pytest.raises(ValueError, match='cycle'):
        c3_linearize('A', {'A': ['A']})


def test_inherited_method_resolution():
    result = parse_file(
        'a.py',
        'class A:\n    def helper(self):\n        pass\nclass B(A):\n    def run(self):\n        self.helper()\n',
    )
    resolver = Resolver([result])
    assert resolver.resolve_name('self.helper', result.symbols[4].id) == result.symbols[2].id


def test_overrides_and_super():
    result = parse_file(
        'a.py',
        'class A:\n    def work(self):\n        pass\nclass B(A):\n    def work(self):\n        super().work()\n    def run(self):\n        self.work()\n',
    )
    resolver = Resolver([result])
    assert resolver.resolve_name('self.work', result.symbols[5].id) == result.symbols[4].id
    assert resolver.resolve_name('super().work', result.symbols[4].id) == result.symbols[2].id


def test_dynamic_call_candidates_have_distinct_edge_kind():
    result = parse_file('a.py', 'def run():\n    pass\ndef caller(obj):\n    obj.run()\n')
    edges = Resolver([result]).resolve()
    uncertain = [edge for edge in edges if edge.kind == 'may_call']
    assert len(uncertain) == 1
    assert uncertain[0].target == result.symbols[1].id
    assert uncertain[0].confidence == 0.25


def test_resolution_confidence_distinguishes_method_dispatch():
    result = parse_file(
        'a.py',
        'def helper():\n    pass\nclass A:\n    def work(self):\n        helper()\n        self.work()\n',
    )
    edges = [edge for edge in Resolver([result]).resolve() if edge.kind == 'calls']
    assert next(edge for edge in edges if edge.target == result.symbols[1].id).confidence == 1
    assert next(edge for edge in edges if edge.target == result.symbols[3].id).confidence == 0.9


def test_structural_edges_persist(tmp_path):
    result = parse_file('a.py', 'class A:\n    def work(self):\n        pass\n')
    resolver = Resolver([result])
    path = tmp_path / 'graph.json'
    resolver.save_graph(path)
    edges = resolver.load_edges(path)
    assert edges == resolver.resolve()
    assert sum(edge.kind == 'contains' for edge in edges) == 2
    assert sum(edge.kind == 'defines' for edge in edges) == 2


def test_call_and_import_edges_roundtrip(tmp_path):
    helper = parse_file('helper.py', 'def work():\n    pass\n')
    client = parse_file('client.py', 'from helper import work\ndef main():\n    work()\n')
    resolver = Resolver([helper, client])
    resolver.save_graph(tmp_path / 'graph.json')
    edges = resolver.load_edges(tmp_path / 'graph.json')
    assert any(edge.kind == 'imports' and edge.target == helper.symbols[1].id for edge in edges)
    assert any(edge.kind == 'calls' and edge.target == helper.symbols[1].id for edge in edges)


def test_inheritance_edges_persist(tmp_path):
    result = parse_file('a.py', 'class A:\n    pass\nclass B(A):\n    pass\n')
    resolver = Resolver([result])
    resolver.save_graph(tmp_path / 'graph.json')
    edges = resolver.load_edges(tmp_path / 'graph.json')
    assert Edge(result.symbols[2].id, result.symbols[1].id, 'inherits') in edges


def test_associations_require_resolved_calls():
    helper = parse_file('helper.py', 'def work():\n    pass\n')
    test = parse_file('test_helper.py', 'from helper import work\ndef test_work():\n    work()\n')
    edges = Resolver([helper, test]).resolve()
    assert Edge(test.symbols[1].id, helper.symbols[1].id, 'tests') in edges


def test_callers_and_callees_ignore_external_refs():
    result = parse_file('a.py', 'def work():\n    len([])\ndef caller():\n    work()\n')
    resolver = Resolver([result])
    assert resolver.callers(result.symbols[1].id) == [result.symbols[2]]
    assert resolver.callees(result.symbols[2].id) == [result.symbols[1]]
    assert resolver.callees(result.symbols[1].id) == []


def test_hand_labelled_call_edges():
    from smriti.resolve import LABELLED_FIXTURE

    result = parse_file('fixture.py', LABELLED_FIXTURE['source'])
    resolver = Resolver([result])
    actual = {
        (resolver.symbols[edge.source].qualname, resolver.symbols[edge.target].qualname)
        for edge in resolver.resolve()
        if edge.kind == 'calls' and edge.target in resolver.symbols
    }
    assert actual == set(LABELLED_FIXTURE['expected_calls'])


def test_reference_agreement_with_jedi():
    import jedi

    from smriti.resolve import JEDI_REFERENCE_CASES

    for source, line, column, expected in JEDI_REFERENCE_CASES:
        reference = jedi.Script(source).goto(line, column, follow_imports=True)
        result = parse_file('fixture.py', source)
        resolver = Resolver([result])
        targets = {
            resolver.symbols[edge.target].name
            for edge in resolver.resolve()
            if edge.kind == 'calls' and edge.target in resolver.symbols
        }
        assert expected in targets
        assert expected in {item.name for item in reference}


def test_report_edge_precision_and_recall():
    from smriti.resolve import LABELLED_FIXTURE, edge_metrics

    result = parse_file('fixture.py', LABELLED_FIXTURE['source'])
    resolver = Resolver([result])
    actual = {
        (resolver.symbols[e.source].qualname, resolver.symbols[e.target].qualname)
        for e in resolver.resolve()
        if e.kind == 'calls' and e.target in resolver.symbols
    }
    report = edge_metrics(actual, set(LABELLED_FIXTURE['expected_calls']))
    assert report['precision'] == report['recall'] == 1.0
    assert report['true_positive'] == 2
    assert edge_metrics({('a', 'b')}, {('a', 'c')})['precision'] == 0


def test_resolution_limits_remain_explicit():
    from smriti.resolve import RESOLUTION_LIMITATIONS

    assert any('MRO' in limitation for limitation in RESOLUTION_LIMITATIONS)
    result = parse_file('a.py', 'def caller(factory):\n    factory()\n')
    assert any(edge.target.startswith('dynamic:') for edge in Resolver([result]).resolve())


def test_decorated_scopes_preserve_local_shadowing():
    result = parse_file(
        'a.py',
        'def helper():\n    pass\n@decorator\ndef caller(helper):\n    helper()\n',
    )
    resolver = Resolver([result])
    caller = result.symbols[2]
    assert caller.start_line == 3
    assert resolver.resolve_name('helper', caller.id) is None


def test_class_base_through_self_inside_method_terminates():
    source = (
        'class Outer:\n'
        '    def build(self):\n'
        '        class Inner(self.Base):\n'
        '            def run(self):\n'
        '                self.go()\n'
        '        return Inner\n'
    )
    edges = Resolver([parse_file('a.py', source)]).resolve()
    assert edges
