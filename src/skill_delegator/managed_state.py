"""Strict read-only scanning of manager-owned and unmanaged target state."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from skill_delegator.models import CurrentTargetState, ManagedEntry, TargetSpec, UnmanagedEntry

_MANAGER = "skill-delegator"
_SCHEMA_VERSION = 1
_SHA256_LENGTH = 64


class TargetStateError(ValueError):
    """Target state is malformed, ambiguous, or unsafe to reconcile."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TargetStateError(f"duplicate metadata key: {key}")
        result[key] = value
    return result


def _safe_relative_artifact(value: object) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise TargetStateError("managed artifact_id must be a nonempty string")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise TargetStateError(f"managed artifact_id is not confined: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise TargetStateError(f"managed artifact_id is not canonical: {value!r}")
    return path


def _validate_real_directory(path: Path, *, label: str) -> Path:
    if not path.is_absolute():
        raise TargetStateError(f"{label} must be absolute: {path}")
    normalized = Path(os.path.abspath(path))
    current = Path(normalized.anchor)
    try:
        for part in normalized.parts[1:]:
            current /= part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise TargetStateError(f"{label} contains a symlink: {current}")
        if not stat.S_ISDIR(normalized.lstat().st_mode):
            raise TargetStateError(f"{label} is not a directory: {normalized}")
    except FileNotFoundError as error:
        raise TargetStateError(f"{label} does not exist: {normalized}") from error
    except OSError as error:
        raise TargetStateError(f"cannot inspect {label} {normalized}: {error}") from error
    return normalized


def _read_metadata(path: Path) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise TargetStateError(f"cannot inspect manager metadata {path}: {error}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise TargetStateError(f"manager metadata must not be a symlink: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise TargetStateError(f"manager metadata must be a regular file: {path}")
    try:
        document = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_object_without_duplicates
        )
    except TargetStateError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TargetStateError(f"cannot parse manager metadata {path}: {error}") from error
    if not isinstance(document, dict):
        raise TargetStateError("manager metadata must be a JSON object")
    return document


def _parse_managed(root: Path) -> tuple[tuple[ManagedEntry, ...], Path | None]:
    namespace = root / ".skill-delegator"
    if not os.path.lexists(namespace):
        return (), None
    try:
        namespace_metadata = namespace.lstat()
    except OSError as error:
        raise TargetStateError(
            f"cannot inspect manager metadata directory {namespace}: {error}"
        ) from error
    if stat.S_ISLNK(namespace_metadata.st_mode):
        raise TargetStateError(f"manager metadata directory must not be a symlink: {namespace}")
    if not stat.S_ISDIR(namespace_metadata.st_mode):
        raise TargetStateError(f"manager metadata path is not a directory: {namespace}")
    metadata_path = namespace / "managed.json"
    if not os.path.lexists(metadata_path):
        raise TargetStateError(f"manager metadata directory has no managed.json: {namespace}")
    document = _read_metadata(metadata_path)
    expected_keys = {"schema_version", "manager", "cache_root", "entries"}
    if set(document) != expected_keys:
        raise TargetStateError("manager metadata has missing or unknown keys")
    if type(document["schema_version"]) is not int or document["schema_version"] != _SCHEMA_VERSION:
        raise TargetStateError("unsupported manager metadata schema_version")
    if document["manager"] != _MANAGER:
        raise TargetStateError("manager metadata ownership marker does not match skill-delegator")
    if not isinstance(document["cache_root"], str):
        raise TargetStateError("manager metadata cache_root must be a string")
    cache_root = Path(document["cache_root"])
    if not cache_root.is_absolute():
        raise TargetStateError("manager metadata cache_root must be absolute")
    cache_root = Path(os.path.abspath(cache_root))
    entries = document["entries"]
    if not isinstance(entries, list):
        raise TargetStateError("manager metadata entries must be an array")

    parsed: list[tuple[str, PurePosixPath, Path, str]] = []
    seen: set[str] = set()
    for raw in entries:
        if not isinstance(raw, dict) or set(raw) != {
            "artifact_id",
            "source_path",
            "content_sha256",
        }:
            raise TargetStateError("managed entry has missing or unknown keys")
        artifact = _safe_relative_artifact(raw["artifact_id"])
        artifact_id = artifact.as_posix()
        if artifact_id in seen:
            raise TargetStateError(f"duplicate managed artifact: {artifact_id}")
        seen.add(artifact_id)
        if not isinstance(raw["source_path"], str):
            raise TargetStateError(f"managed source_path must be a string: {artifact_id}")
        source_path = Path(raw["source_path"])
        if not source_path.is_absolute():
            raise TargetStateError(f"managed source_path must be absolute: {artifact_id}")
        source_path = Path(os.path.abspath(source_path))
        if not source_path.is_relative_to(cache_root) or source_path == cache_root:
            raise TargetStateError(
                f"managed source path is outside manager cache root: {source_path}"
            )
        digest = raw["content_sha256"]
        if (
            not isinstance(digest, str)
            or len(digest) != _SHA256_LENGTH
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise TargetStateError(f"managed content_sha256 is invalid: {artifact_id}")
        parsed.append((artifact_id, artifact, source_path, digest))

    managed: list[ManagedEntry] = []
    for artifact_id, artifact, source_path, digest in parsed:
        _validate_real_directory(source_path, label="managed source path")
        link_path = root.joinpath(*artifact.parts)
        current = root
        try:
            for part in artifact.parts[:-1]:
                current /= part
                component = current.lstat()
                if stat.S_ISLNK(component.st_mode):
                    raise TargetStateError(f"symlinked managed path component: {current}")
                if not stat.S_ISDIR(component.st_mode):
                    raise TargetStateError(f"managed path component is not a directory: {current}")
            link_metadata = link_path.lstat()
        except FileNotFoundError as error:
            raise TargetStateError(f"managed link is missing: {link_path}") from error
        except OSError as error:
            raise TargetStateError(f"cannot inspect managed link {link_path}: {error}") from error
        if not stat.S_ISLNK(link_metadata.st_mode):
            raise TargetStateError(f"managed entry is not a symlink: {link_path}")
        raw_target = Path(os.readlink(link_path))
        actual_target = raw_target if raw_target.is_absolute() else link_path.parent / raw_target
        actual_target = Path(os.path.abspath(actual_target))
        if not actual_target.exists():
            raise TargetStateError(f"broken managed link: {link_path}")
        if actual_target != source_path:
            raise TargetStateError(f"managed link does not match manager metadata: {link_path}")
        managed.append(ManagedEntry(artifact_id, artifact, source_path, digest))
    return tuple(sorted(managed, key=lambda item: item.artifact_id)), cache_root


def _scan_unmanaged(root: Path, managed: tuple[ManagedEntry, ...]) -> tuple[UnmanagedEntry, ...]:
    managed_paths = {entry.relative_path for entry in managed}
    entries: list[UnmanagedEntry] = []

    def visit(directory: Path, relative_directory: PurePosixPath) -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda item: os.fsencode(item.name))
        except OSError as error:
            raise TargetStateError(f"cannot scan target directory {directory}: {error}") from error
        for child in children:
            if not relative_directory.parts and child.name == ".skill-delegator":
                continue
            relative = relative_directory / child.name
            if relative in managed_paths:
                continue
            try:
                mode = child.stat(follow_symlinks=False).st_mode
            except OSError as error:
                raise TargetStateError(
                    f"cannot inspect target entry {child.path}: {error}"
                ) from error
            if stat.S_ISLNK(mode):
                entries.append(UnmanagedEntry(relative, "symlink", os.readlink(child.path)))
            elif stat.S_ISDIR(mode):
                entries.append(UnmanagedEntry(relative, "directory", None))
                visit(Path(child.path), relative)
            elif stat.S_ISREG(mode):
                entries.append(UnmanagedEntry(relative, "file", None))
            else:
                entries.append(UnmanagedEntry(relative, "other", None))

    visit(root, PurePosixPath())
    return tuple(sorted(entries, key=lambda item: item.relative_path.as_posix()))


def scan_target(target: TargetSpec) -> CurrentTargetState:
    """Inspect one target without creating, replacing, or removing anything."""

    root = Path(os.path.abspath(target.root))
    if not os.path.lexists(root):
        return CurrentTargetState(target.id, root, (), ())
    try:
        root_metadata = root.lstat()
    except OSError as error:
        raise TargetStateError(f"cannot inspect target root {root}: {error}") from error
    if stat.S_ISLNK(root_metadata.st_mode):
        raise TargetStateError(f"target root must not be a symlink: {root}")
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise TargetStateError(f"target root is not a directory: {root}")
    managed, cache_root = _parse_managed(root)
    return CurrentTargetState(target.id, root, managed, _scan_unmanaged(root, managed), cache_root)
