"""Descriptor-relative validation, hashing, discovery, and copying of source trees."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from skill_delegator.errors import SourceError
from skill_delegator.identifiers import canonical_relative_path
from skill_delegator.inventory import (
    _frontmatter_bytes,
    _hash_record,
    _validate_relative_root,
)
from skill_delegator.models import SkillArtifact
from skill_delegator.source_ignore import IgnoreRules

_OPEN_BASE = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
_OPEN_DIRECTORY = _OPEN_BASE | getattr(os, "O_DIRECTORY", 0)


@dataclass(frozen=True)
class _TreeEntry:
    path: bytes
    mode: int
    kind: bytes
    payload: bytes
    device: int
    inode: int


def _display(path: bytes) -> str:
    return ascii(os.fsdecode(path))


def _names_at(directory_fd: int) -> list[bytes]:
    scan_fd = -1
    try:
        # Reopen the retained directory so enumeration never depends on a caller's
        # shared directory-stream offset (which dir_fd mutations can advance).
        scan_fd = os.open(".", _OPEN_DIRECTORY, dir_fd=directory_fd)
        names = [os.fsencode(name) for name in os.listdir(scan_fd)]
    except OSError as error:
        raise SourceError(f"cannot list source directory: {error}") from error
    finally:
        if scan_fd >= 0:
            os.close(scan_fd)
    return sorted(name for name in names if name != b".git")


def _same_identity(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        first.st_mode,
        first.st_size,
        first.st_mtime_ns,
    ) == (
        second.st_dev,
        second.st_ino,
        second.st_mode,
        second.st_size,
        second.st_mtime_ns,
    )


def _read_file_at(directory_fd: int, name: bytes, metadata: os.stat_result, path: bytes) -> bytes:
    try:
        file_fd = os.open(name, _OPEN_BASE, dir_fd=directory_fd)
    except OSError as error:
        raise SourceError(f"cannot open source file {_display(path)}: {error}") from error
    try:
        opened = os.fstat(file_fd)
        if not stat.S_ISREG(opened.st_mode) or not _same_identity(metadata, opened):
            raise SourceError(f"source mutated during traversal: {_display(path)}")
        chunks: list[bytes] = []
        while chunk := os.read(file_fd, 1024 * 1024):
            chunks.append(chunk)
        after = os.fstat(file_fd)
        if not _same_identity(opened, after):
            raise SourceError(f"source mutated during traversal: {_display(path)}")
        return b"".join(chunks)
    except OSError as error:
        raise SourceError(f"cannot read source file {_display(path)}: {error}") from error
    finally:
        os.close(file_fd)


def _walk_at(
    directory_fd: int,
    prefix: bytes = b"",
    inherited: IgnoreRules | None = None,
    *,
    reject_ignored: bool = False,
) -> list[_TreeEntry]:
    before_names = _names_at(directory_fd)
    prefix_parts = tuple(prefix.split(b"/")) if prefix else ()
    rules = inherited or IgnoreRules()
    if b".gitignore" in before_names:
        try:
            ignore_metadata = os.stat(b".gitignore", dir_fd=directory_fd, follow_symlinks=False)
        except OSError as error:
            raise SourceError(f"cannot inspect source path '.gitignore': {error}") from error
        if stat.S_ISREG(ignore_metadata.st_mode):
            payload = _read_file_at(directory_fd, b".gitignore", ignore_metadata, b".gitignore")
            rules = rules.extend(prefix_parts, payload)
    entries: list[_TreeEntry] = []
    for name in before_names:
        path = name if not prefix else prefix + b"/" + name
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as error:
            raise SourceError(f"cannot inspect source path {_display(path)}: {error}") from error
        path_parts = (*prefix_parts, name)
        directory_entry = stat.S_ISDIR(metadata.st_mode)
        if rules.ignored(path_parts, directory=directory_entry):
            if reject_ignored:
                raise SourceError(f"ignored entry present in filtered snapshot: {_display(path)}")
            continue
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            try:
                target = os.readlink(name, dir_fd=directory_fd)
                after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as error:
                raise SourceError(
                    f"cannot read source symlink {_display(path)}: {error}"
                ) from error
            if not _same_identity(metadata, after):
                raise SourceError(f"source mutated during traversal: {_display(path)}")
            entries.append(
                _TreeEntry(path, mode, b"L", os.fsencode(target), metadata.st_dev, metadata.st_ino)
            )
        elif stat.S_ISDIR(metadata.st_mode):
            try:
                child_fd = os.open(name, _OPEN_DIRECTORY, dir_fd=directory_fd)
            except OSError as error:
                raise SourceError(
                    f"cannot open source directory {_display(path)}: {error}"
                ) from error
            try:
                opened = os.fstat(child_fd)
                if not stat.S_ISDIR(opened.st_mode) or not _same_identity(metadata, opened):
                    raise SourceError(f"source mutated during traversal: {_display(path)}")
                entries.append(_TreeEntry(path, mode, b"D", b"", metadata.st_dev, metadata.st_ino))
                entries.extend(_walk_at(child_fd, path, rules, reject_ignored=reject_ignored))
                if not _same_identity(opened, os.fstat(child_fd)):
                    raise SourceError(f"source mutated during traversal: {_display(path)}")
            finally:
                os.close(child_fd)
        elif stat.S_ISREG(metadata.st_mode):
            payload = _read_file_at(directory_fd, name, metadata, path)
            entries.append(_TreeEntry(path, mode, b"F", payload, metadata.st_dev, metadata.st_ino))
        else:
            raise SourceError(f"unsupported special file in source: {_display(path)}")
    if _names_at(directory_fd) != before_names:
        raise SourceError("source mutated during traversal")
    return entries


def _normalise_target(parent: tuple[bytes, ...], target: bytes) -> tuple[bytes, ...]:
    if target.startswith(b"/"):
        raise SourceError(f"symlink escape from source root: {os.fsdecode(target)!r}")
    parts = list(parent)
    for part in target.split(b"/"):
        if part in {b"", b"."}:
            continue
        if part == b"..":
            if not parts:
                raise SourceError(f"symlink escape from source root: {os.fsdecode(target)!r}")
            parts.pop()
        else:
            parts.append(part)
    return tuple(parts)


def _absolute_target_is_internal(
    target: bytes,
    entries: dict[tuple[bytes, ...], _TreeEntry],
    root_identity: tuple[int, int],
) -> bool:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    try:
        target_fd = os.open(target, flags)
    except OSError as error:
        raise SourceError(f"broken symlink in source: {os.fsdecode(target)!r}: {error}") from error
    try:
        metadata = os.fstat(target_fd)
    finally:
        os.close(target_fd)
    identity = (metadata.st_dev, metadata.st_ino)
    return identity == root_identity or any(
        identity == (entry.device, entry.inode) for entry in entries.values()
    )


def _validate_symlink(
    path: tuple[bytes, ...],
    entries: dict[tuple[bytes, ...], _TreeEntry],
    *,
    snapshot: bool,
    root_identity: tuple[int, int],
) -> None:
    pending = list(path)
    resolved: list[bytes] = []
    followed: set[tuple[bytes, ...]] = set()
    while pending:
        resolved.append(pending.pop(0))
        current = tuple(resolved)
        entry = entries.get(current)
        if entry is None:
            raise SourceError(f"broken symlink in source: {os.fsdecode(b'/'.join(path))!r}")
        if entry.kind != b"L":
            continue
        if current in followed:
            raise SourceError(f"broken symlink in source: {os.fsdecode(b'/'.join(path))!r}")
        followed.add(current)
        if entry.payload.startswith(b"/"):
            if snapshot:
                raise SourceError(
                    f"symlink escape from copied snapshot root: {os.fsdecode(entry.path)!r}"
                )
            if not _absolute_target_is_internal(entry.payload, entries, root_identity):
                raise SourceError(f"symlink escape from source root: {os.fsdecode(entry.path)!r}")
            return
        target = _normalise_target(tuple(resolved[:-1]), entry.payload)
        resolved = []
        pending = [*target, *pending]


def validate_tree_at(root_fd: int, *, snapshot: bool, reject_ignored: bool = False) -> None:
    """Validate a retained source tree without resolving children through a path."""

    entries = _walk_at(root_fd, reject_ignored=reject_ignored)
    by_path = {tuple(entry.path.split(b"/")): entry for entry in entries}
    root_metadata = os.fstat(root_fd)
    root_identity = (root_metadata.st_dev, root_metadata.st_ino)
    for path, entry in by_path.items():
        if entry.kind == b"L":
            _validate_symlink(
                path,
                by_path,
                snapshot=snapshot,
                root_identity=root_identity,
            )


def _hash_entries(entries: list[_TreeEntry], prefix: bytes = b"") -> str:
    digest = hashlib.sha256()
    marker = prefix + b"/" if prefix else b""
    for entry in sorted(entries, key=lambda item: item.path):
        if prefix:
            if not entry.path.startswith(marker):
                continue
            relative = entry.path[len(marker) :]
        else:
            relative = entry.path
        _hash_record(digest, entry.kind, relative, entry.mode, entry.payload)
    return digest.hexdigest()


def hash_tree_at(root_fd: int) -> str:
    """Return the inventory-compatible hash of a retained source tree."""

    return _hash_entries(_walk_at(root_fd))


def _path_parts(path: PurePosixPath) -> tuple[bytes, ...]:
    return tuple(os.fsencode(part) for part in path.parts if part != ".")


def _is_below(path: tuple[bytes, ...], root: tuple[bytes, ...]) -> bool:
    return len(path) > len(root) and path[: len(root)] == root


def discover_skills_at(root_fd: int, skill_root: PurePosixPath) -> tuple[SkillArtifact, ...]:
    """Discover skill artifacts below ``skill_root`` from a retained descriptor."""

    _validate_relative_root(skill_root)
    entries = _walk_at(root_fd)
    by_path = {tuple(entry.path.split(b"/")): entry for entry in entries}
    root_parts = _path_parts(skill_root)
    if root_parts:
        root_entry = by_path.get(root_parts)
        if root_entry is None:
            raise SourceError(f"skill root cannot be resolved: {skill_root}")
        if root_entry.kind != b"D":
            raise SourceError(f"skill root is not a directory: {skill_root}")

    root_metadata = os.fstat(root_fd)
    root_identity = (root_metadata.st_dev, root_metadata.st_ino)
    for path, entry in by_path.items():
        if entry.kind == b"L" and _is_below(path, root_parts):
            _validate_symlink(
                path,
                by_path,
                snapshot=False,
                root_identity=root_identity,
            )

    artifacts: list[SkillArtifact] = []
    seen: set[PurePosixPath] = set()
    for path, entry in sorted(by_path.items(), key=lambda item: item[0]):
        if entry.kind != b"F" or path[-1] != b"SKILL.md" or not _is_below(path, root_parts):
            continue
        directory_parts = path[len(root_parts) : -1]
        if not directory_parts:
            raise SourceError("SKILL.md: skill must be in a directory below skill_root")
        relative_text = "/".join(os.fsdecode(part) for part in directory_parts)
        relative = PurePosixPath(relative_text)
        try:
            relative.as_posix().encode("utf-8")
        except UnicodeEncodeError as error:
            raise SourceError(
                f"skill path cannot form a UTF-8 canonical id: {relative.as_posix()!a}"
            ) from error
        if not canonical_relative_path(relative):
            raise SourceError(f"skill path cannot form a canonical id: {relative.as_posix()!r}")
        if relative in seen:
            raise SourceError(f"duplicate artifact path: {relative}")
        seen.add(relative)
        display = os.fsdecode(entry.path)
        name, description = _frontmatter_bytes(entry.payload, display)
        directory_path = b"/".join(path[:-1])
        artifacts.append(
            SkillArtifact(
                relative_path=relative,
                runtime_name=name,
                description=description,
                sha256=_hash_entries(entries, directory_path),
            )
        )
    return tuple(sorted(artifacts, key=lambda artifact: artifact.relative_path.as_posix()))


def _write_all(file_fd: int, payload: bytes, path: bytes) -> None:
    remaining = memoryview(payload)
    try:
        while remaining:
            written = os.write(file_fd, remaining)
            if written == 0:
                raise OSError("short write")
            remaining = remaining[written:]
    except OSError as error:
        raise SourceError(f"cannot copy source file {_display(path)}: {error}") from error


def copy_tree_into_at(source_fd: int, destination_fd: int) -> None:
    """Copy a retained source tree into an existing empty retained directory."""

    entries = sorted(_walk_at(source_fd), key=lambda entry: entry.path)
    directories: list[_TreeEntry] = []
    for entry in entries:
        try:
            if entry.kind == b"D":
                os.mkdir(entry.path, mode=0o700, dir_fd=destination_fd)
                directories.append(entry)
            elif entry.kind == b"L":
                os.symlink(entry.payload, entry.path, dir_fd=destination_fd)
            else:
                flags = (
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0)
                )
                file_fd = os.open(entry.path, flags, mode=0o600, dir_fd=destination_fd)
                try:
                    _write_all(file_fd, entry.payload, entry.path)
                    os.fchmod(file_fd, 0o755 if entry.mode & 0o111 else 0o644)
                finally:
                    os.close(file_fd)
        except SourceError:
            raise
        except OSError as error:
            raise SourceError(f"cannot copy source path {_display(entry.path)}: {error}") from error
    for entry in reversed(directories):
        directory_fd = os.open(entry.path, _OPEN_DIRECTORY, dir_fd=destination_fd)
        try:
            os.fchmod(directory_fd, 0o755)
        finally:
            os.close(directory_fd)


def copy_tree_at(source_fd: int, destination: Path) -> None:
    """Copy a retained source tree into a new private destination."""

    try:
        destination.mkdir(mode=0o700)
        destination_fd = os.open(destination, _OPEN_DIRECTORY)
    except OSError as error:
        raise SourceError(f"cannot create snapshot destination {destination}: {error}") from error
    try:
        copy_tree_into_at(source_fd, destination_fd)
    finally:
        os.close(destination_fd)
