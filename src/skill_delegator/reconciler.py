"""Transactional reconciliation of manager-owned symlinks only."""

from __future__ import annotations

import fcntl
import json
import os
import stat
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from skill_delegator.errors import SourceError
from skill_delegator.inventory import hash_tree
from skill_delegator.managed_state import TargetStateError, scan_target, target_fingerprint
from skill_delegator.models import (
    ManagedEntry,
    PlanOperation,
    PlanTarget,
    ReconciliationPlan,
    TargetSpec,
)

_MUTATIONS = {"CREATE", "REPLACE", "REMOVE"}
_MAX_ERROR = 500


class ApplyError(RuntimeError):
    """The reviewed apply could not complete safely."""


@dataclass(frozen=True)
class ApplyResult:
    """Bounded result of a successful transaction (audit receipts are Task 6)."""

    changed: int
    targets: int


@dataclass
class _LockedTarget:
    target: PlanTarget
    stream: BinaryIO
    root_created: bool
    namespace_created: bool
    managed_created: bool
    previous_managed: bytes | None


@dataclass(frozen=True)
class _JournalEntry:
    operation: PlanOperation
    final: Path
    backup: Path | None
    desired_raw_target: str | None


def _checkpoint(_name: str) -> None:
    """Failure-injection seam used by temporary-filesystem tests."""


def _bounded(value: object) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= _MAX_ERROR else text[: _MAX_ERROR - 3] + "..."


def _lstat_directory(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ApplyError(f"cannot inspect {label} {path}: {_bounded(error)}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise ApplyError(f"{label} must not be a symlink: {path}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ApplyError(f"{label} must be a directory: {path}")


def _ensure_directory_chain(path: Path) -> list[Path]:
    """Create missing lexical directories without traversing a symlink component."""

    normalized = Path(os.path.abspath(path))
    current = Path(normalized.anchor)
    created: list[Path] = []
    _lstat_directory(current, label="target root component")
    for part in normalized.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir()
            except OSError as error:
                raise ApplyError(
                    f"cannot create target directory {current}: {_bounded(error)}"
                ) from error
            created.append(current)
            metadata = current.lstat()
        except OSError as error:
            raise ApplyError(
                f"cannot inspect target root component {current}: {_bounded(error)}"
            ) from error
        if stat.S_ISLNK(metadata.st_mode):
            raise ApplyError(f"target root contains a symlink: {current}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ApplyError(f"target root component is not a directory: {current}")
    return created


def _canonical_managed(target: PlanTarget) -> bytes:
    document = {
        "schema_version": 1,
        "manager": "skill-delegator",
        "cache_root": str(target.cache_root),
        "entries": [
            {
                "artifact_id": entry.artifact_id,
                "source_path": str(entry.source_path),
                "content_sha256": entry.content_sha256,
            }
            for entry in sorted(target.desired_entries, key=lambda item: item.artifact_id)
        ],
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _prepare_lock(target: PlanTarget) -> _LockedTarget:
    created = _ensure_directory_chain(target.root)
    root_created = target.root in created
    namespace = target.root / ".skill-delegator"
    namespace_created = False
    try:
        namespace.mkdir()
        namespace_created = True
    except FileExistsError:
        _lstat_directory(namespace, label="manager metadata directory")
    except OSError as error:
        raise ApplyError(
            f"cannot create manager metadata directory {namespace}: {_bounded(error)}"
        ) from error

    lock_path = namespace / "operation.lock"
    try:
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, flags, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ApplyError(f"operation lock must be a regular file: {lock_path}")
        stream = os.fdopen(descriptor, "a+b")
    except OSError as error:
        raise ApplyError(f"cannot open operation lock {lock_path}: {_bounded(error)}") from error
    return _LockedTarget(target, stream, root_created, namespace_created, False, None)


def _initialize_metadata(locked: _LockedTarget) -> None:
    """Snapshot or bootstrap managed state only while holding the target lock."""

    managed = locked.target.root / ".skill-delegator" / "managed.json"
    if os.path.lexists(managed):
        try:
            metadata = managed.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                raise ApplyError(f"manager metadata must be a regular file: {managed}")
            locked.previous_managed = managed.read_bytes()
        except OSError as error:
            raise ApplyError(
                f"cannot read manager metadata {managed}: {_bounded(error)}"
            ) from error
    else:
        _atomic_write(
            managed,
            _canonical_managed(replace(locked.target, desired_entries=())),
        )
        locked.managed_created = True


def _acquire(stream: BinaryIO, *, deadline: float, target_id: str) -> None:
    while True:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError as error:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ApplyError(f"operation lock timeout for target {target_id}") from error
            time.sleep(min(0.01, remaining))
        except OSError as error:
            raise ApplyError(
                f"cannot acquire operation lock for target {target_id}: {_bounded(error)}"
            ) from error


def _fresh_fingerprint(locked: _LockedTarget) -> str:
    try:
        fresh = scan_target(TargetSpec(locked.target.id, locked.target.root, ()))
    except TargetStateError as error:
        raise ApplyError(f"cannot re-scan target {locked.target.id}: {_bounded(error)}") from error
    if locked.root_created:
        fresh = replace(fresh, root_exists=False)
    if locked.managed_created:
        fresh = replace(fresh, cache_root=None, managed=())
    return target_fingerprint(fresh)


def _safe_source(entry: ManagedEntry, cache_root: Path) -> None:
    source = entry.source_path
    if not source.is_absolute() or not source.is_relative_to(cache_root) or source == cache_root:
        raise ApplyError(f"desired source is outside exact cache root: {source}")
    current = Path(source.anchor)
    try:
        for part in source.parts[1:]:
            current /= part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise ApplyError(f"desired source contains a symlink: {current}")
        if not stat.S_ISDIR(source.lstat().st_mode):
            raise ApplyError(f"desired source is not a directory: {source}")
    except FileNotFoundError as error:
        raise ApplyError(f"desired source is missing: {source}") from error
    except OSError as error:
        raise ApplyError(f"cannot inspect desired source {source}: {_bounded(error)}") from error
    try:
        actual_hash = hash_tree(source)
    except (OSError, SourceError) as error:
        raise ApplyError(f"cannot hash desired source {source}: {_bounded(error)}") from error
    if actual_hash != entry.content_sha256:
        raise ApplyError(f"desired source content hash differs from reviewed lock: {source}")


def _safe_manager_directory(path: Path) -> None:
    try:
        path.mkdir()
    except FileExistsError:
        _lstat_directory(path, label="manager transaction directory")
    except OSError as error:
        raise ApplyError(
            f"cannot create manager transaction directory {path}: {_bounded(error)}"
        ) from error


def _stage(locked: _LockedTarget, token: str) -> Path:
    namespace = locked.target.root / ".skill-delegator"
    staging_parent = namespace / "staging"
    _safe_manager_directory(staging_parent)
    staging = staging_parent / token
    try:
        staging.mkdir()
    except OSError as error:
        raise ApplyError(f"cannot create staging directory {staging}: {_bounded(error)}") from error
    for entry in locked.target.desired_entries:
        _safe_source(entry, locked.target.cache_root)
        staged = staging.joinpath(*entry.relative_path.parts)
        _ensure_confined_parent(staging, entry.relative_path, [])
        try:
            os.symlink(str(entry.source_path), staged)
        except OSError as error:
            raise ApplyError(
                f"cannot stage managed link {entry.artifact_id}: {_bounded(error)}"
            ) from error
        metadata = staged.lstat()
        raw = os.readlink(staged)
        if not stat.S_ISLNK(metadata.st_mode) or raw != str(entry.source_path):
            raise ApplyError(
                f"staged link target differs from reviewed source: {entry.artifact_id}"
            )
    return staging


def _ensure_confined_parent(root: Path, relative: PurePosixPath, created: list[Path]) -> Path:
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ApplyError(f"managed path is not confined: {relative}")
    _lstat_directory(root, label="managed root")
    current = root
    for part in relative.parts[:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir()
            except OSError as error:
                raise ApplyError(
                    f"cannot create managed parent {current}: {_bounded(error)}"
                ) from error
            created.append(current)
            metadata = current.lstat()
        except OSError as error:
            raise ApplyError(
                f"cannot inspect managed parent {current}: {_bounded(error)}"
            ) from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ApplyError(f"managed parent is not a real directory: {current}")
    return current


def _assert_current(operation: PlanOperation, final: Path) -> None:
    try:
        metadata = final.lstat()
    except OSError as error:
        raise ApplyError(f"reviewed managed link changed before promotion: {final}") from error
    if not stat.S_ISLNK(metadata.st_mode):
        raise ApplyError(f"reviewed managed link is no longer a symlink: {final}")
    raw = Path(os.readlink(final))
    actual = raw if raw.is_absolute() else final.parent / raw
    actual = Path(os.path.abspath(actual))
    if operation.current_source_path is None or actual != operation.current_source_path:
        raise ApplyError(f"reviewed managed link target changed before promotion: {final}")


def _promote(
    locked: _LockedTarget,
    operation: PlanOperation,
    staging: Path,
    backup: Path,
    created: list[Path],
) -> _JournalEntry:
    parent = _ensure_confined_parent(locked.target.root, operation.relative_path, created)
    final = parent / operation.relative_path.name
    staged = staging.joinpath(*operation.relative_path.parts)
    backup_path: Path | None = None
    if operation.action == "CREATE":
        if os.path.lexists(final):
            raise ApplyError(f"CREATE destination became occupied: {final}")
    else:
        _assert_current(operation, final)
        backup_parent = _ensure_confined_parent(backup, operation.relative_path, [])
        backup_path = backup_parent / operation.relative_path.name
        try:
            os.replace(final, backup_path)
        except OSError as error:
            raise ApplyError(f"cannot back up managed link {final}: {_bounded(error)}") from error
    desired_raw: str | None = None
    if operation.action in {"CREATE", "REPLACE"}:
        try:
            desired_raw = os.readlink(staged)
            os.replace(staged, final)
        except OSError as error:
            if backup_path is not None and not os.path.lexists(final):
                os.replace(backup_path, final)
            raise ApplyError(f"cannot promote managed link {final}: {_bounded(error)}") from error
    return _JournalEntry(operation, final, backup_path, desired_raw)


def _rollback_entry(entry: _JournalEntry) -> None:
    if entry.operation.action in {"CREATE", "REPLACE"} and os.path.lexists(entry.final):
        metadata = entry.final.lstat()
        if (
            not stat.S_ISLNK(metadata.st_mode)
            or os.readlink(entry.final) != entry.desired_raw_target
        ):
            raise OSError(f"refusing to delete changed destination during rollback: {entry.final}")
        entry.final.unlink()
    if entry.backup is not None and os.path.lexists(entry.backup):
        if os.path.lexists(entry.final):
            raise OSError(f"rollback destination is occupied: {entry.final}")
        os.replace(entry.backup, entry.final)


def _restore_metadata(locked: _LockedTarget) -> None:
    managed = locked.target.root / ".skill-delegator" / "managed.json"
    if locked.previous_managed is None:
        try:
            managed.unlink()
        except FileNotFoundError:
            pass
    else:
        _atomic_write(managed, locked.previous_managed)


def _remove_tree_owned(path: Path) -> None:
    """Remove one freshly-created manager transaction tree without following links."""

    if not os.path.lexists(path):
        return
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise OSError(f"manager transaction path changed type: {path}")
    for child in path.iterdir():
        child_metadata = child.lstat()
        if stat.S_ISDIR(child_metadata.st_mode) and not stat.S_ISLNK(child_metadata.st_mode):
            _remove_tree_owned(child)
        else:
            child.unlink()
    path.rmdir()


def _failure_receipt(path: Path, phase: str, error: BaseException, rollback: list[str]) -> None:
    document = {
        "status": "failed",
        "phase": _bounded(phase),
        "error": _bounded(error),
        "rollback_errors": [_bounded(item) for item in rollback[:10]],
    }
    _atomic_write(
        path,
        (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
    )


def _validate_plan_bindings(plan: ReconciliationPlan) -> None:
    targets = {target.id: target for target in plan.targets}
    if len(targets) != len(plan.targets):
        raise ApplyError("reviewed plan has inconsistent duplicate target bindings")
    seen: set[tuple[str, PurePosixPath]] = set()
    for operation in plan.operations:
        if operation.action not in _MUTATIONS:
            continue
        target = targets.get(operation.target_id)
        if target is None or operation.artifact_id is None:
            raise ApplyError("reviewed plan has inconsistent operation target binding")
        key = (operation.target_id, operation.relative_path)
        if key in seen:
            raise ApplyError("reviewed plan has inconsistent duplicate mutation path")
        seen.add(key)
        desired = {entry.artifact_id: entry for entry in target.desired_entries}
        if len(desired) != len(target.desired_entries):
            raise ApplyError("reviewed plan has inconsistent duplicate desired artifacts")
        entry = desired.get(operation.artifact_id)
        if operation.action in {"CREATE", "REPLACE"}:
            if (
                entry is None
                or entry.relative_path != operation.relative_path
                or entry.source_path != operation.desired_source_path
            ):
                raise ApplyError("reviewed plan has inconsistent desired operation binding")
        elif entry is not None or operation.current_source_path is None:
            raise ApplyError("reviewed plan has inconsistent REMOVE operation binding")


def apply_plan(plan: ReconciliationPlan, *, lock_timeout: float) -> ApplyResult:
    """Apply one immutable reviewed plan under stable-order per-target locks."""

    if plan.blocked:
        raise ApplyError(f"plan is blocked: {_bounded(plan.blocked[0])}")
    _validate_plan_bindings(plan)
    mutations = tuple(operation for operation in plan.operations if operation.action in _MUTATIONS)
    if not plan.targets:
        if mutations:
            raise ApplyError("plan has no immutable apply target bindings")
        return ApplyResult(0, 0)
    if not mutations:
        return ApplyResult(0, len(plan.targets))
    if lock_timeout < 0:
        raise ApplyError("lock_timeout must be non-negative")

    locked_targets: list[_LockedTarget] = []
    journals: list[_JournalEntry] = []
    created_parents: list[Path] = []
    transaction_dirs: list[Path] = []
    phase = "locking"
    rollback_errors: list[str] = []
    token = uuid.uuid4().hex
    try:
        deadline = time.monotonic() + lock_timeout
        for target in sorted(plan.targets, key=lambda item: (str(item.root), item.id)):
            locked = _prepare_lock(target)
            try:
                _acquire(locked.stream, deadline=deadline, target_id=target.id)
            except ApplyError:
                locked.stream.close()
                raise
            locked_targets.append(locked)
            _initialize_metadata(locked)

        phase = "fresh-state validation"
        for locked in locked_targets:
            if _fresh_fingerprint(locked) != locked.target.current_fingerprint:
                raise ApplyError(f"stale plan for target {locked.target.id}; current state changed")

        phase = "staging"
        staging_by_id: dict[str, Path] = {}
        backup_by_id: dict[str, Path] = {}
        for locked in locked_targets:
            staging = _stage(locked, token)
            staging_by_id[locked.target.id] = staging
            transaction_dirs.append(staging)
            backup_parent = locked.target.root / ".skill-delegator" / "backup"
            _safe_manager_directory(backup_parent)
            backup = backup_parent / token
            backup.mkdir()
            backup_by_id[locked.target.id] = backup
            transaction_dirs.append(backup)
        _checkpoint("after-stage")

        phase = "promotion"
        locked_by_id = {locked.target.id: locked for locked in locked_targets}
        for promoted, operation in enumerate(mutations, start=1):
            locked = locked_by_id[operation.target_id]
            journal = _promote(
                locked,
                operation,
                staging_by_id[operation.target_id],
                backup_by_id[operation.target_id],
                created_parents,
            )
            journals.append(journal)
            _checkpoint(f"after-promote-{promoted}")

        phase = "metadata publication"
        _checkpoint("before-metadata")
        for locked in locked_targets:
            _atomic_write(
                locked.target.root / ".skill-delegator" / "managed.json",
                _canonical_managed(locked.target),
            )
        _checkpoint("after-metadata")

        phase = "cleanup"
        for directory in reversed(transaction_dirs):
            _remove_tree_owned(directory)
        return ApplyResult(len(mutations), len(locked_targets))
    except Exception as error:
        phase_at_failure = phase
        for entry in reversed(journals):
            try:
                _rollback_entry(entry)
            except OSError as rollback_error:
                rollback_errors.append(_bounded(rollback_error))
        for locked in locked_targets:
            try:
                _restore_metadata(locked)
            except OSError as rollback_error:
                rollback_errors.append(_bounded(rollback_error))
        for directory in reversed(transaction_dirs):
            try:
                _remove_tree_owned(directory)
            except OSError as rollback_error:
                rollback_errors.append(_bounded(rollback_error))
        for directory in reversed(created_parents):
            try:
                directory.rmdir()
            except FileNotFoundError:
                pass
            except OSError as rollback_error:
                rollback_errors.append(_bounded(rollback_error))
        for locked in locked_targets:
            try:
                _failure_receipt(
                    locked.target.root / ".skill-delegator" / "failure.json",
                    phase_at_failure,
                    error,
                    rollback_errors,
                )
            except OSError as receipt_error:
                rollback_errors.append(f"failure receipt: {_bounded(receipt_error)}")
        suffix = f"; rollback failed: {'; '.join(rollback_errors)}" if rollback_errors else ""
        if isinstance(error, ApplyError):
            raise ApplyError(f"{_bounded(error)}{suffix}") from error
        raise ApplyError(
            f"apply failed during {phase_at_failure}: {_bounded(error)}{suffix}"
        ) from error
    finally:
        for locked in reversed(locked_targets):
            try:
                fcntl.flock(locked.stream.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            locked.stream.close()
