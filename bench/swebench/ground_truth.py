"""Read fix patches for evaluation only; never apply them to retrieval inputs."""

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChangedFile:
    old_path: str | None
    new_path: str | None
    removed_lines: tuple[int, ...]
    added_at_base_lines: tuple[int, ...]


def _patch_path(text: str) -> str | None:
    value = text.split('\t', 1)[0]
    if value == '/dev/null':
        return None
    if value.startswith('"'):
        value = json.loads(value)
    return value[2:] if value.startswith(('a/', 'b/')) else value


def parse_changed_files(patch: str) -> tuple[ChangedFile, ...]:
    """Use changed lines, not context lines, to avoid inflating gold functions."""
    files: list[ChangedFile] = []
    old_path: str | None = None
    new_path: str | None = None
    removed: list[int] = []
    added: list[int] = []
    old_line = 0
    active = False
    hunk = False

    def flush() -> None:
        if active:
            files.append(ChangedFile(old_path, new_path, tuple(removed), tuple(added)))

    for line in patch.splitlines():
        if line.startswith('diff --git '):
            flush()
            old_path = new_path = None
            removed, added = [], []
            active = hunk = False
        elif line.startswith('--- ') and not hunk:
            old_path = _patch_path(line[4:])
            active = True
        elif line.startswith('+++ ') and not hunk:
            new_path = _patch_path(line[4:])
        elif line.startswith('@@ '):
            match = re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@', line)
            if match is None:
                raise ValueError('Malformed unified diff hunk')
            old_line = int(match.group(1))
            hunk = True
        elif hunk:
            if line.startswith('-'):
                removed.append(old_line)
                old_line += 1
            elif line.startswith('+'):
                # Insertions are associated with their base location. Entirely
                # new functions require separate reporting, not post-fix indexing.
                added.append(old_line)
            elif line.startswith(' '):
                old_line += 1
            elif not line.startswith('\\ No newline'):
                hunk = False
    flush()
    return tuple(files)
