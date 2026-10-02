from smriti.parse import SourceParser, validate_ranges
from smriti.resolve import Resolver


def test_go_package_calls_receiver_methods_and_imports():
    parser = SourceParser()
    first = parser.parse(
        'worker.go',
        'package billing\nimport "fmt"\ntype Worker struct{}\nfunc (w *Worker) Work() int { return w.Other() }\nfunc (w *Worker) Other() int { return total() }\n',
        'go',
    )
    second = parser.parse('total.go', 'package billing\nfunc total() int { return 1 }\n', 'go')
    edges = Resolver([first, second]).resolve()
    symbols = {symbol.name: symbol for result in (first, second) for symbol in result.symbols}
    assert any(
        edge.source == symbols['Work'].id
        and edge.target == symbols['Other'].id
        and edge.kind == 'calls'
        for edge in edges
    )
    assert any(
        edge.source == symbols['Other'].id
        and edge.target == symbols['total'].id
        and edge.kind == 'calls'
        for edge in edges
    )
    assert first.imports[0]['module'] == 'fmt'
    validate_ranges(first)


def test_c_direct_calls_and_unknown_function_pointer_stay_distinct():
    result = SourceParser().parse(
        'billing.c',
        '#include "billing.h"\nint total(int x) {return x;}\nint invoice() {return total(1);}\nint dynamic(int (*fn)()) {return fn();}\n',
        'c',
    )
    symbols = {symbol.name: symbol for symbol in result.symbols}
    edges = Resolver([result]).resolve()
    assert any(
        edge.source == symbols['invoice'].id
        and edge.target == symbols['total'].id
        and edge.kind == 'calls'
        for edge in edges
    )
    assert any(
        edge.source == symbols['dynamic'].id and edge.target == 'external:c:fn' for edge in edges
    )
    assert result.imports[0]['module'] == 'billing.h'
    validate_ranges(result)


def test_cpp_namespace_and_overloads_are_conservative():
    result = SourceParser().parse(
        'billing.cpp',
        'namespace billing { int total(int x) {return x;} int total(double x) {return 2;} int invoice() {return total(1);} }',
        'cpp',
    )
    totals = [symbol for symbol in result.symbols if symbol.name == 'total']
    assert len(totals) == 2 and len({symbol.id for symbol in totals}) == 2
    assert all(symbol.qualname == 'billing.billing.total' for symbol in totals)
    edges = Resolver([result]).resolve()
    assert sum(edge.kind == 'may_call' for edge in edges) == 2
    assert not any(
        edge.kind == 'calls' and edge.target in {symbol.id for symbol in totals} for edge in edges
    )
    validate_ranges(result)


def test_language_switch_does_not_reuse_incompatible_tree():
    parser = SourceParser()
    parser.parse('source', 'def work():\n return 1\n')
    switched = parser.parse('source', 'int work() {return 1;}', 'c')
    fresh = SourceParser().parse('source', switched.source, 'c')
    assert switched.symbols == fresh.symbols


def test_go_incremental_result_matches_fresh():
    parser = SourceParser()
    parser.parse('a.go', 'package main\nfunc work() int {return 1}', 'go')
    result = parser.parse('a.go', 'package main\nfunc work() int {return 2}', 'go')
    assert result.symbols == SourceParser().parse('a.go', result.source, 'go').symbols


def test_function_pointer_parameter_shadows_same_named_c_function():
    result = SourceParser().parse(
        'a.c', 'int total(){return 1;} int invoke(int (*total)()){return total();}', 'c'
    )
    edges = Resolver([result]).resolve()
    invoke = next(symbol for symbol in result.symbols if symbol.name == 'invoke')
    total = next(symbol for symbol in result.symbols if symbol.name == 'total')
    assert not any(edge.source == invoke.id and edge.target == total.id for edge in edges)
    assert any(edge.source == invoke.id and edge.target == 'external:c:total' for edge in edges)


def test_go_function_parameter_shadows_package_function():
    result = SourceParser().parse(
        'a.go',
        'package main\nfunc total() int{return 1}\nfunc invoke(total func() int) int{return total()}',
        'go',
    )
    invoke = next(symbol for symbol in result.symbols if symbol.name == 'invoke')
    edges = Resolver([result]).resolve()
    assert any(edge.source == invoke.id and edge.target == 'external:go:total' for edge in edges)
