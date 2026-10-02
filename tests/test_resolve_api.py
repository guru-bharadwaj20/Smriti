import pytest

from smriti.parse import SourceParser
from smriti.resolve.api import ApiBinding, cross_language_edges


def test_declared_http_boundary_links_python_to_go():
    parser = SourceParser()
    python = parser.parse('client.py', 'def invoice():\n return 1\n')
    go = parser.parse('server.go', 'package main\nfunc Total() int {return 1}', 'go')
    consumer = next(symbol for symbol in python.symbols if symbol.kind == 'function')
    provider = next(symbol for symbol in go.symbols if symbol.kind == 'function')
    edges = cross_language_edges(
        [*python.symbols, *go.symbols],
        [
            ApiBinding(consumer.id, 'http:POST', '/v1/total', 'consumer'),
            ApiBinding(provider.id, 'http:POST', '/v1/total', 'provider'),
        ],
    )
    assert len(edges) == 1 and edges[0].source == consumer.id and edges[0].target == provider.id
    assert edges[0].kind == 'calls' and edges[0].confidence == 0.8
    assert not cross_language_edges(
        [*python.symbols, *go.symbols],
        [
            ApiBinding(consumer.id, 'http:GET', '/v1/total', 'consumer'),
            ApiBinding(provider.id, 'http:POST', '/v1/total', 'provider'),
        ],
    )


def test_missing_api_anchor_fails_and_ambiguous_providers_remain_uncertain():
    parser = SourceParser()
    python = parser.parse('client.py', 'def invoice():\n return 1\n')
    go = parser.parse(
        'server.go',
        'package main\nfunc Total() int {return 1}\nfunc Replica() int {return 1}',
        'go',
    )
    consumer = next(symbol for symbol in python.symbols if symbol.kind == 'function')
    providers = [symbol for symbol in go.symbols if symbol.kind == 'function']
    symbols = [*python.symbols, *go.symbols]
    with pytest.raises(ValueError, match='anchor does not exist'):
        cross_language_edges(symbols, [ApiBinding('missing', 'grpc', 'billing.Total', 'provider')])
    bindings = [
        ApiBinding(consumer.id, 'grpc', 'billing.Total', 'consumer'),
        *[ApiBinding(symbol.id, 'grpc', 'billing.Total', 'provider') for symbol in providers],
    ]
    edges = cross_language_edges(symbols, bindings)
    assert len(edges) == 2 and all(
        edge.kind == 'may_call' and edge.confidence == 0.25 for edge in edges
    )
