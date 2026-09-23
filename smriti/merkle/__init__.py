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


def hash_directory(children: dict[str, str]) -> str:
    """Domain-separated length framing prevents ambiguous concatenations."""
    digest = sha256(b"smriti-directory-v1\0")
    for name, value in ordered_children(children):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(bytes.fromhex(value))
    return digest.hexdigest()


import json
import os
from dataclasses import dataclass, field


@dataclass
class MerkleSnapshot:
    files: dict[str, str] = field(default_factory=dict)
    directories: dict[str, str] = field(default_factory=dict)

    @property
    def root_hash(self) -> str:
        return self.directories.get("", hash_directory({}))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump({"version": 1, "files": self.files, "directories": self.directories}, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    @classmethod
    def load(cls, path: str | Path) -> "MerkleSnapshot":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise ValueError("Unsupported Merkle snapshot version")
        for collection in (data["files"], data["directories"]):
            for value in collection.values():
                if len(value) != 64 or len(bytes.fromhex(value)) != 32:
                    raise ValueError("Malformed content hash")
        return cls(data["files"], data["directories"])


class RepositoryScanner:
    def __init__(self, ignored: tuple[str, ...] = (".git", ".venv", ".smriti", "__pycache__", ".pytest_cache")):
        self.ignored = frozenset(ignored)

    def scan(self, root: str | Path) -> MerkleSnapshot:
        root = Path(root).resolve()
        snapshot = MerkleSnapshot()

        from pathspec import GitIgnoreSpec

        def walk(directory: Path, rules=()) -> str:
            ignore_file = directory / ".gitignore"
            if ignore_file.is_file():
                rules = (*rules, (directory, GitIgnoreSpec.from_lines(ignore_file.read_text(encoding="utf-8").splitlines())))
            children = {}
            for child in sorted(directory.iterdir(), key=lambda p: p.name.encode("utf-8")):
                relative = child.relative_to(root).as_posix()
                if child.name in self.ignored:
                    continue
                ignored = False
                for base, spec in rules:
                    value = child.relative_to(base).as_posix() + ("/" if child.is_dir() else "")
                    result = spec.check_file(value).include
                    if result is not None:
                        ignored = result
                if ignored:
                    continue
                if child.is_symlink():
                    children[child.name] = snapshot.files[relative] = hash_content(b"symlink\0" + os.fsencode(os.readlink(child)))
                elif child.is_dir():
                    children[child.name] = walk(child, rules)
                elif child.is_file():
                    children[child.name] = snapshot.files[relative] = hash_file(child)
            relative = directory.relative_to(root).as_posix()
            snapshot.directories["" if relative == "." else relative] = hash_directory(children)
            return snapshot.directories["" if relative == "." else relative]

        walk(root)
        return snapshot


def changed_paths(old: MerkleSnapshot, new: MerkleSnapshot) -> set[str]:
    """Skip equal subtrees, comparing file leaves only under changed directories."""
    if old.root_hash == new.root_hash:
        return set()
    unchanged = {directory for directory, digest in old.directories.items()
                 if new.directories.get(directory) == digest}
    def skip(path: str) -> bool:
        return any(path.startswith(directory + "/") for directory in unchanged if directory)
    return {path for path in old.files.keys() | new.files.keys()
            if not skip(path) and old.files.get(path) != new.files.get(path)}
