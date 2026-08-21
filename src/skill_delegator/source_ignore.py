"""Source-local Git-compatible ignore policy.

Only ``.gitignore`` files inside the source tree contribute rules.  Ambient Git
configuration, global excludes, and repository metadata are never consulted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pathspec import GitIgnoreSpec


def _git_compatible_pattern(line: str) -> str:
    """Keep a trailing ``/**`` from matching its own parent directory."""

    pattern = line.lstrip() if line.endswith("\\ ") else line.strip()
    if pattern.endswith("/**"):
        # pathspec compiles ``abc/**`` as ``^abc/.*$``, which also matches the
        # traversal candidate ``abc/``.  Git excludes only entries below abc.
        return f"{pattern}/*"
    return line


@dataclass(frozen=True)
class _ScopedSpec:
    base: tuple[bytes, ...]
    spec: GitIgnoreSpec


@dataclass(frozen=True)
class IgnoreRules:
    """Ordered nested ``.gitignore`` rules rooted at a source tree."""

    scopes: tuple[_ScopedSpec, ...] = ()

    def extend(self, base: tuple[bytes, ...], payload: bytes) -> IgnoreRules:
        text = payload.decode("utf-8", errors="surrogateescape")
        lines = [_git_compatible_pattern(line) for line in text.splitlines()]
        return IgnoreRules((*self.scopes, _ScopedSpec(base, GitIgnoreSpec.from_lines(lines))))

    def _direct_match(self, path: tuple[bytes, ...], *, directory: bool) -> bool | None:
        if path and path[-1] == b".gitignore":
            return False
        outcome: bool | None = None
        for scoped in self.scopes:
            if len(path) <= len(scoped.base) or path[: len(scoped.base)] != scoped.base:
                continue
            relative = b"/".join(path[len(scoped.base) :])
            candidate = os.fsdecode(relative) + ("/" if directory else "")
            result = scoped.spec.check_file(candidate)
            if result.include is not None:
                outcome = result.include
        return outcome

    def ignored(self, path: tuple[bytes, ...], *, directory: bool) -> bool:
        """Return Git-compatible ignored state, including excluded-parent behavior."""

        for length in range(1, len(path)):
            if self._direct_match(path[:length], directory=True) is True:
                return True
        return self._direct_match(path, directory=directory) is True


def path_parts(path: Path, root: Path) -> tuple[bytes, ...]:
    """Return byte-preserving root-relative path components."""

    return tuple(os.fsencode(part) for part in path.relative_to(root).parts)
