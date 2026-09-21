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


def ordered_children(children: dict[str, str]) -> list[tuple[str, str]]:
    """Sort by exact UTF-8 names, independent of insertion or filesystem order."""
    return sorted(children.items(), key=lambda pair: pair[0].encode("utf-8"))
