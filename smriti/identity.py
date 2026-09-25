"""Stable repository identity and initial symbol identifiers."""

import uuid
from hashlib import sha256
from pathlib import Path


def repository_id(root: Path) -> str:
    """Persist identity across branch switches; intentionally not across copies."""
    directory = root.resolve() / '.smriti'
    directory.mkdir(parents=True, exist_ok=True)
    identity = directory / 'repository-id'
    try:
        with identity.open('x', encoding='utf-8') as stream:
            stream.write(uuid.uuid4().hex)
    except FileExistsError:
        pass
    value = identity.read_text(encoding='utf-8').strip()
    if len(value) != 32 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Invalid repository identity')
    return value


def symbol_id(repository: str, path: str, kind: str, qualname: str) -> str:
    """Initial ID. Verified move/rename reconciliation retains existing IDs."""
    payload = '\0'.join((repository, path.replace('\\', '/'), kind, qualname))
    return sha256(payload.encode('utf-8')).hexdigest()
