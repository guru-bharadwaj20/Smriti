"""Offline shared-secret authenticated memory bundles.

HMAC identifies a trusted group, not an individual author: every key holder can
sign bundles for that group. Callers provision and rotate keys out of band.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from . import MemoryStore
from .operations import Operation, canonical, digest

DOMAIN = b'SMRITI-MEMORY-SYNC-v1\0'


def _key(key: bytes) -> None:
    if len(key) < 32:
        raise ValueError('Synchronization requires at least 32 random key bytes')


def export_bundle(store: MemoryStore, repository: str, key: bytes) -> dict[str, Any]:
    _key(key)
    if not repository:
        raise ValueError('A repository identity is required')
    with store._atomic():
        document = {
            'schema_version': 1,
            'repository': repository,
            'head': store.head,
            'operations': [
                json.loads(row[0])
                for row in store.db.execute('SELECT canonical FROM memory_operations ORDER BY seq')
            ],
            'blobs': {
                row[0]: json.loads(row[1])
                for row in store.db.execute(
                    'SELECT digest,payload FROM memory_blobs ORDER BY digest'
                )
            },
            'purged_ids': [
                row[0]
                for row in store.db.execute('SELECT fact_id FROM memory_purged ORDER BY fact_id')
            ],
        }
    signature = hmac.new(
        key, DOMAIN + canonical(document).encode('utf-8'), hashlib.sha256
    ).hexdigest()
    return {'algorithm': 'HMAC-SHA256', 'document': document, 'signature': signature}


def verify_bundle(bundle: dict[str, Any], repository: str, key: bytes) -> dict[str, Any]:
    _key(key)
    if bundle.get('algorithm') != 'HMAC-SHA256':
        raise ValueError('Unsupported authentication algorithm')
    document = bundle['document']
    signature = hmac.new(
        key, DOMAIN + canonical(document).encode('utf-8'), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, str(bundle.get('signature', ''))):
        raise ValueError('Bundle authentication failed')
    if document['schema_version'] != 1 or document['repository'] != repository:
        raise ValueError('Bundle belongs to another schema or repository')
    for identity, payload in document['blobs'].items():
        if digest(payload) != identity:
            raise ValueError('Payload checksum mismatch')
    return dict(document)


def import_bundle(
    store: MemoryStore, bundle: dict[str, Any], repository: str, key: bytes, branch: str
) -> str | None:
    document = verify_bundle(bundle, repository, key)
    branch = store._branch_name(branch)
    if branch == store.current_branch:
        raise ValueError('Import into a peer branch before explicitly merging or switching')
    with store._atomic():
        existing_ids = {row[0] for row in store.db.execute('SELECT oid FROM memory_operations')}
        for record in document['operations']:
            record = dict(record)
            record['parents'] = tuple(record['parents'])
            operation = Operation(**record)
            if any(parent not in existing_ids for parent in operation.parents):
                raise ValueError('Bundle contains missing or unordered operation parents')
            if operation.kind not in {
                'add',
                'update',
                'invalidate',
                'revert',
                'merge',
                'restore',
                'forget',
            }:
                raise ValueError('Unsupported operation kind')
            store.db.execute(
                'INSERT OR IGNORE INTO memory_operations(oid,canonical) VALUES (?,?)',
                (operation.id, canonical(operation.record())),
            )
            existing_ids.add(operation.id)
        head = document['head']
        if head is not None and head not in existing_ids:
            raise ValueError('Bundle head is missing')
        prior = store.branches().get(branch)
        if prior is not None and prior != head:
            if prior not in {op.id for op in store.operations.ancestry(head)}:
                raise ValueError('Import would rewind or replace a divergent peer branch')
        purged = set(document['purged_ids']) | {
            row[0] for row in store.db.execute('SELECT fact_id FROM memory_purged')
        }
        for identity, payload in document['blobs'].items():
            if payload.get('id') not in purged:
                store.db.execute(
                    'INSERT OR IGNORE INTO memory_blobs VALUES (?,?)',
                    (identity, canonical(payload)),
                )
            if 'text' in payload and 'id' in payload:
                for source in payload.get('derived_from', []):
                    store.db.execute(
                        'INSERT OR IGNORE INTO memory_derivations VALUES (?,?)',
                        (source, payload['id']),
                    )
        closure = set(purged)
        for identity in purged:
            closure.update(store.dependents(identity))
        # Existing tombstones must also delete payloads received indirectly from
        # a peer who had not learned about the source deletion yet.
        for identity in closure:
            store.db.execute(
                "DELETE FROM memory_blobs WHERE json_extract(payload,'$.id')=?", (identity,)
            )
        store._purge(closure)
        store.db.execute('INSERT OR REPLACE INTO memory_branches VALUES (?,?)', (branch, head))
        store._materialize(store.replay(store.head))
    if purged:
        store._physical_cleanup()
    return str(head) if head is not None else None
