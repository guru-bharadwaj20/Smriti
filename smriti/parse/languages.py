"""Structural extraction for Go and C-family grammars without a compiler."""

from __future__ import annotations

from hashlib import sha256
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from tree_sitter import Node

from smriti.models import Symbol, SymbolKind

if TYPE_CHECKING:
    from . import ParseResult


def extract(result: ParseResult) -> None:
    source, path = result.source, result.path

    def text(node: Node) -> str:
        return source[node.start_byte : node.end_byte].decode('utf-8')

    def make(
        node: Node, name: str, kind: SymbolKind, parent: Symbol | None, body: Node | None = None
    ) -> Symbol:
        qualname = (parent.qualname + '.' if parent else '') + name
        signature = (
            source[node.start_byte : (body.start_byte if body else node.end_byte)]
            .decode('utf-8')
            .rstrip()
        )
        # Overloads and duplicate declarations need distinct identities.
        identity = sha256(
            (path + ':' + kind + ':' + qualname + ':' + signature).encode()
        ).hexdigest()
        symbol = Symbol(
            identity,
            path,
            name,
            qualname,
            kind,
            source[: node.start_byte].count(b'\n') + 1,
            source[: node.end_byte].count(b'\n') + 1,
            node.start_byte,
            node.end_byte,
            signature=signature,
            body=text(node),
            content_hash=sha256(source[node.start_byte : node.end_byte]).hexdigest(),
            parent_id=parent.id if parent else None,
        )
        result.symbols.append(symbol)
        return symbol

    package_nodes = [
        node for node in result.tree.root_node.named_children if node.type == 'package_clause'
    ]
    result.package = text(package_nodes[0].named_children[0]) if package_nodes else ''
    module = make(result.tree.root_node, result.package or PurePosixPath(path).stem, 'module', None)
    types: dict[str, Symbol] = {}

    def declarator_name(node: Node) -> Node | None:
        current = node
        while True:
            child = current.child_by_field_name('declarator')
            if (
                child is None
                and current.type == 'parenthesized_declarator'
                and current.named_children
            ):
                child = current.named_children[0]
            if child is None:
                break
            current = child
        return (
            current
            if current.type
            in {
                'identifier',
                'field_identifier',
                'qualified_identifier',
                'operator_name',
                'destructor_name',
            }
            else None
        )

    def walk(node: Node, parent: Symbol) -> None:
        if node.type in {
            'type_spec',
            'class_specifier',
            'struct_specifier',
            'namespace_definition',
        }:
            name = node.child_by_field_name('name')
            body = node.child_by_field_name('body') or node.child_by_field_name('type')
            if name is not None:
                parent = make(node, text(name), 'class', parent, body)
                types[parent.name] = parent
        elif node.type in {'function_declaration', 'method_declaration', 'function_definition'}:
            name = node.child_by_field_name('name')
            if name is None:
                declarator = node.child_by_field_name('declarator')
                name = declarator_name(declarator) if declarator is not None else None
            body = node.child_by_field_name('body')
            if name is not None and body is not None:
                receiver = node.child_by_field_name('receiver')
                binding: tuple[str, str] | None = None
                if receiver is not None and receiver.named_children:
                    parameter = receiver.named_children[0]
                    variable, receiver_type = (
                        parameter.child_by_field_name('name'),
                        parameter.child_by_field_name('type'),
                    )
                    if variable is not None and receiver_type is not None:
                        typename = text(receiver_type).lstrip('*')
                        binding = (text(variable), typename)
                        parent = types.get(typename, parent)
                parent = make(
                    node,
                    text(name),
                    'method' if receiver is not None or parent.kind == 'class' else 'function',
                    parent,
                    body,
                )
                if binding:
                    result.receiver_bindings[parent.id] = binding
        elif node.type in {
            'parameter_declaration',
            'variadic_parameter_declaration',
            'var_spec',
            'declaration',
        } and parent.kind in {'function', 'method'}:
            names = node.children_by_field_name('name')
            for declaration in node.children_by_field_name('declarator'):
                declared = declarator_name(declaration)
                if declared is not None:
                    names.append(declared)
            result.local_names.setdefault(parent.id, set()).update(text(name) for name in names)
        elif node.type == 'short_var_declaration' and parent.kind in {'function', 'method'}:
            left = node.child_by_field_name('left')
            if left is not None:
                result.local_names.setdefault(parent.id, set()).update(
                    text(name) for name in left.named_children if name.type == 'identifier'
                )
        elif node.type == 'import_spec':
            imported = node.child_by_field_name('path')
            alias = node.child_by_field_name('name')
            if imported is not None:
                target = text(imported).strip('"`')
                result.imports.append(
                    {
                        'scope': module.id,
                        'module': target,
                        'name': '',
                        'alias': text(alias) if alias else target.rsplit('/', 1)[-1],
                        'level': 0,
                        'line': source[: node.start_byte].count(b'\n') + 1,
                    }
                )
        elif node.type == 'preproc_include':
            imported = node.child_by_field_name('path')
            if imported is not None:
                target = text(imported).strip('"<>')
                result.imports.append(
                    {
                        'scope': module.id,
                        'module': target,
                        'name': '',
                        'alias': target,
                        'level': 0,
                        'line': source[: node.start_byte].count(b'\n') + 1,
                    }
                )
        elif node.type == 'call_expression':
            function = node.child_by_field_name('function')
            if function is not None:
                result.calls.append(
                    {
                        'scope': parent.id,
                        'name': text(function),
                        'line': source[: node.start_byte].count(b'\n') + 1,
                        'start_byte': node.start_byte,
                    }
                )
        if node.type == 'ERROR' or node.is_missing:
            result.diagnostics.append(
                {
                    'kind': 'missing' if node.is_missing else 'syntax_error',
                    'start_byte': node.start_byte,
                    'end_byte': node.end_byte,
                    'line': source[: node.start_byte].count(b'\n') + 1,
                }
            )
        for child in node.children:
            walk(child, parent)

    for child in result.tree.root_node.children:
        walk(child, module)
