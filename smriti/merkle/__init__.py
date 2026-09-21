"""Content-addressed repository snapshots."""

from hashlib import sha256
from pathlib import Path


def hash_content(content: bytes) -> str:
    """Hash exact bytes; file names and modification times are irrelevant."""
    return sha256(content).hexdigest()


def hash_file(path: str | Path) -> str:
    """Stream file bytes so large source files do not require extra copies."""
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
