"""Descriptor-anchored transactional reconciliation of manager-owned symlinks."""

from __future__ import annotations

import json
import math
import os
import stat
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from skill_delegator.errors import SourceError

try:
    import fcntl
except ImportError:  # pragma: no cover - isolated import contract covers this path
    fcntl = None  # type: ignore[assignment]

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
_DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
if hasattr(os, "O_NOFOLLOW"):
    _DIR_FLAGS |= os.O_NOFOLLOW


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
    root_fd: int
    namespace_fd: int
    lock_fd: int
    root_identity: tuple[int, int]
    namespace_identity: tuple[int, int]
    created_chain: list[tuple[Path, tuple[int, int]]]
    namespace_created: bool
    lock_created: bool
    managed_created: bool = False
    previous_managed: bytes | None = None
    transaction: _TransactionDirs | None = None

    @property
    def initially_absent(self) -> bool:
        return bool(self.created_chain)


@dataclass
class _TransactionDirs:
    token: str
    staging_parent_fd: int
    staging_fd: int
    backup_parent_fd: int
    backup_fd: int
    staging_parent_created: bool
    backup_parent_created: bool
    staging_removed: bool = False
    backup_removed: bool = False


@dataclass(frozen=True)
class _JournalEntry:
    operation: PlanOperation
    locked: _LockedTarget
    transaction: _TransactionDirs
    promoted_identity: tuple[int, int] | None
    desired_raw_target: str | None


@dataclass(frozen=True)
class _CreatedParent:
    locked: _LockedTarget
    relative: PurePosixPath


def _checkpoint(_name: str) -> None:
    """Failure-injection seam used by temporary-filesystem tests."""


def _bounded(value: object) -> str:
    text = str(value).replace("\n", " ")
    return text if len(text) <= _MAX_ERROR else text[: _MAX_ERROR - 3] + "..."


def _identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _lstat_directory(path: Path, *, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ApplyError(f"cannot inspect {label} {path}: {_bounded(error)}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise ApplyError(f"{label} must not be a symlink: {path}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ApplyError(f"{label} must be a directory: {path}")
    return metadata


def _ensure_directory_chain(path: Path) -> list[tuple[Path, tuple[int, int]]]:
    """Create missing lexical directories without traversing a symlink component."""

    normalized = Path(os.path.abspath(path))
    current = Path(normalized.anchor)
    created: list[tuple[Path, tuple[int, int]]] = []
    _lstat_directory(current, label="target root component")
    try:
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
                metadata = current.lstat()
                created.append((current, _identity(metadata)))
            except OSError as error:
                raise ApplyError(
                    f"cannot inspect target root component {current}: {_bounded(error)}"
                ) from error
            if stat.S_ISLNK(metadata.st_mode):
                raise ApplyError(f"target root contains a symlink: {current}")
            if not stat.S_ISDIR(metadata.st_mode):
                raise ApplyError(f"target root component is not a directory: {current}")
        return created
    except Exception:
        _remove_created_chain(created, [])
        raise


def _remove_created_chain(created: list[tuple[Path, tuple[int, int]]], errors: list[str]) -> None:
    for path, expected in reversed(created):
        try:
            metadata = path.lstat()
            if _identity(metadata) != expected or not stat.S_ISDIR(metadata.st_mode):
                raise OSError(f"refusing to remove replaced created directory: {path}")
            path.rmdir()
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(_bounded(error))


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
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _exists_at(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _atomic_write_at(directory_fd: int, name: str, payload: bytes) -> None:
    temporary = f".{name}.{uuid.uuid4().hex}.tmp"
    descriptor = -1
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


def _read_bytes_at(directory_fd: int, name: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ApplyError(f"manager metadata must be a regular file: {name}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(descriptor)


def _acquire_fd(descriptor: int, *, deadline: float, target_id: str, label: str) -> None:
    if fcntl is None:
        raise ApplyError("V1 requires POSIX advisory locking")
    while True:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError as error:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ApplyError(f"{label} timeout for target {target_id}") from error
            time.sleep(min(0.01, remaining))
        except OSError as error:
            raise ApplyError(
                f"cannot acquire {label} for target {target_id}: {_bounded(error)}"
            ) from error


def _close_locked(locked: _LockedTarget) -> None:
    if locked.transaction is not None:
        for descriptor in (
            locked.transaction.staging_fd,
            locked.transaction.staging_parent_fd,
            locked.transaction.backup_fd,
            locked.transaction.backup_parent_fd,
        ):
            try:
                os.close(descriptor)
            except OSError:
                pass
        locked.transaction = None
    for descriptor in (locked.lock_fd, locked.namespace_fd, locked.root_fd):
        try:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(descriptor)
        except OSError:
            pass


def _prepare_lock(target: PlanTarget, *, deadline: float) -> _LockedTarget:
    created = _ensure_directory_chain(target.root)
    root_fd = namespace_fd = lock_fd = -1
    namespace_created = lock_created = False
    try:
        root_fd = os.open(target.root, _DIR_FLAGS)
        root_metadata = os.fstat(root_fd)
        _acquire_fd(root_fd, deadline=deadline, target_id=target.id, label="target root lock")

        try:
            os.mkdir(".skill-delegator", dir_fd=root_fd)
            namespace_created = True
        except FileExistsError:
            metadata = os.stat(".skill-delegator", dir_fd=root_fd, follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise ApplyError(
                    f"manager metadata directory must be a real directory: {target.root}"
                )
        namespace_fd = os.open(".skill-delegator", _DIR_FLAGS, dir_fd=root_fd)
        namespace_metadata = os.fstat(namespace_fd)

        lock_created = not _exists_at(namespace_fd, "operation.lock")
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            lock_fd = os.open("operation.lock", flags, 0o600, dir_fd=namespace_fd)
        except OSError as error:
            raise ApplyError(
                f"cannot open operation lock {target.root}: {_bounded(error)}"
            ) from error
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise ApplyError(f"operation lock must be a regular file: {target.root}")
        _acquire_fd(lock_fd, deadline=deadline, target_id=target.id, label="operation lock")
        return _LockedTarget(
            target,
            root_fd,
            namespace_fd,
            lock_fd,
            _identity(root_metadata),
            _identity(namespace_metadata),
            created,
            namespace_created,
            lock_created,
        )
    except Exception:
        if lock_fd >= 0:
            os.close(lock_fd)
        if namespace_fd >= 0:
            if lock_created:
                try:
                    os.unlink("operation.lock", dir_fd=namespace_fd)
                except OSError:
                    pass
            os.close(namespace_fd)
        if root_fd >= 0:
            if namespace_created:
                try:
                    os.rmdir(".skill-delegator", dir_fd=root_fd)
                except OSError:
                    pass
            os.close(root_fd)
        _remove_created_chain(created, [])
        raise


def _verify_identity(locked: _LockedTarget) -> None:
    try:
        root_metadata = locked.target.root.lstat()
        namespace_metadata = os.stat(
            ".skill-delegator", dir_fd=locked.root_fd, follow_symlinks=False
        )
    except OSError as error:
        raise ApplyError(
            f"target identity changed for {locked.target.id}: {_bounded(error)}"
        ) from error
    if (
        not stat.S_ISDIR(root_metadata.st_mode)
        or _identity(root_metadata) != locked.root_identity
        or not stat.S_ISDIR(namespace_metadata.st_mode)
        or _identity(namespace_metadata) != locked.namespace_identity
    ):
        raise ApplyError(f"target identity changed for {locked.target.id}")


def _verify_all(locked_targets: list[_LockedTarget]) -> None:
    for locked in locked_targets:
        _verify_identity(locked)


def _initialize_metadata(locked: _LockedTarget) -> None:
    if _exists_at(locked.namespace_fd, "managed.json"):
        try:
            locked.previous_managed = _read_bytes_at(locked.namespace_fd, "managed.json")
        except OSError as error:
            raise ApplyError(f"cannot read manager metadata: {_bounded(error)}") from error
    else:
        _atomic_write_at(
            locked.namespace_fd,
            "managed.json",
            _canonical_managed(replace(locked.target, desired_entries=())),
        )
        locked.managed_created = True


def _fresh_fingerprint(locked: _LockedTarget) -> str:
    _verify_identity(locked)
    try:
        fresh = scan_target(TargetSpec(locked.target.id, locked.target.root, ()))
    except TargetStateError as error:
        raise ApplyError(f"cannot re-scan target {locked.target.id}: {_bounded(error)}") from error
    _verify_identity(locked)
    if locked.initially_absent:
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


def _open_or_create_dir(parent_fd: int, name: str) -> tuple[int, bool]:
    created = False
    try:
        os.mkdir(name, dir_fd=parent_fd)
        created = True
    except FileExistsError:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ApplyError(f"manager transaction path is not a real directory: {name}")
    return os.open(name, _DIR_FLAGS, dir_fd=parent_fd), created


def _validate_relative(relative: PurePosixPath) -> None:
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ApplyError(f"managed path is not confined: {relative}")


def _open_parent_at(
    base_fd: int,
    relative: PurePosixPath,
    *,
    create: bool,
    locked: _LockedTarget | None = None,
    created: list[_CreatedParent] | None = None,
) -> int:
    _validate_relative(relative)
    current = os.dup(base_fd)
    accumulated: list[str] = []
    try:
        for part in relative.parts[:-1]:
            accumulated.append(part)
            try:
                next_fd = os.open(part, _DIR_FLAGS, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, dir_fd=current)
                next_fd = os.open(part, _DIR_FLAGS, dir_fd=current)
                if locked is not None and created is not None:
                    created.append(_CreatedParent(locked, PurePosixPath(*accumulated)))
            os.close(current)
            current = next_fd
        return current
    except Exception:
        os.close(current)
        raise


def _make_transaction(locked: _LockedTarget, token: str) -> _TransactionDirs:
    staging_parent_fd, staging_parent_created = _open_or_create_dir(locked.namespace_fd, "staging")
    backup_parent_fd = staging_fd = backup_fd = -1
    backup_parent_created = False
    try:
        os.mkdir(token, dir_fd=staging_parent_fd)
        staging_fd = os.open(token, _DIR_FLAGS, dir_fd=staging_parent_fd)
        backup_parent_fd, backup_parent_created = _open_or_create_dir(locked.namespace_fd, "backup")
        os.mkdir(token, dir_fd=backup_parent_fd)
        backup_fd = os.open(token, _DIR_FLAGS, dir_fd=backup_parent_fd)
        transaction = _TransactionDirs(
            token,
            staging_parent_fd,
            staging_fd,
            backup_parent_fd,
            backup_fd,
            staging_parent_created,
            backup_parent_created,
        )
        locked.transaction = transaction
        return transaction
    except Exception:
        for descriptor in (backup_fd, backup_parent_fd, staging_fd):
            if descriptor >= 0:
                os.close(descriptor)
        try:
            os.rmdir(token, dir_fd=staging_parent_fd)
        except OSError:
            pass
        os.close(staging_parent_fd)
        if staging_parent_created:
            try:
                os.rmdir("staging", dir_fd=locked.namespace_fd)
            except OSError:
                pass
        raise


def _stage(locked: _LockedTarget, transaction: _TransactionDirs) -> None:
    for entry in locked.target.desired_entries:
        _safe_source(entry, locked.target.cache_root)
        parent_fd = _open_parent_at(transaction.staging_fd, entry.relative_path, create=True)
        try:
            os.symlink(str(entry.source_path), entry.relative_path.name, dir_fd=parent_fd)
            metadata = os.stat(entry.relative_path.name, dir_fd=parent_fd, follow_symlinks=False)
            raw = os.readlink(entry.relative_path.name, dir_fd=parent_fd)
            if not stat.S_ISLNK(metadata.st_mode) or raw != str(entry.source_path):
                raise ApplyError(
                    f"staged link target differs from reviewed source: {entry.artifact_id}"
                )
        except OSError as error:
            raise ApplyError(
                f"cannot stage managed link {entry.artifact_id}: {_bounded(error)}"
            ) from error
        finally:
            os.close(parent_fd)


def _assert_current(operation: PlanOperation, parent_fd: int, name: str, root: Path) -> None:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        raw_text = os.readlink(name, dir_fd=parent_fd)
    except OSError as error:
        raise ApplyError(f"reviewed managed link changed before promotion: {root}") from error
    if not stat.S_ISLNK(metadata.st_mode):
        raise ApplyError(f"reviewed managed link is no longer a symlink: {root}")
    raw = Path(raw_text)
    actual = raw if raw.is_absolute() else root / operation.relative_path.parent / raw
    actual = Path(os.path.abspath(actual))
    if operation.current_source_path is None or actual != operation.current_source_path:
        raise ApplyError(f"reviewed managed link target changed before promotion: {root}")


def _promote(
    locked: _LockedTarget,
    operation: PlanOperation,
    transaction: _TransactionDirs,
    created: list[_CreatedParent],
) -> _JournalEntry:
    final_parent = _open_parent_at(
        locked.root_fd,
        operation.relative_path,
        create=True,
        locked=locked,
        created=created,
    )
    staged_parent = backup_parent = -1
    name = operation.relative_path.name
    try:
        if operation.action == "CREATE":
            if _exists_at(final_parent, name):
                raise ApplyError(f"CREATE destination became occupied: {locked.target.root}")
        else:
            _assert_current(operation, final_parent, name, locked.target.root)
            backup_parent = _open_parent_at(
                transaction.backup_fd, operation.relative_path, create=True
            )
            os.replace(name, name, src_dir_fd=final_parent, dst_dir_fd=backup_parent)

        desired_raw: str | None = None
        promoted_identity: tuple[int, int] | None = None
        if operation.action in {"CREATE", "REPLACE"}:
            staged_parent = _open_parent_at(
                transaction.staging_fd, operation.relative_path, create=False
            )
            desired_raw = os.readlink(name, dir_fd=staged_parent)
            try:
                os.replace(name, name, src_dir_fd=staged_parent, dst_dir_fd=final_parent)
            except OSError:
                if backup_parent >= 0 and not _exists_at(final_parent, name):
                    os.replace(name, name, src_dir_fd=backup_parent, dst_dir_fd=final_parent)
                raise
            metadata = os.stat(name, dir_fd=final_parent, follow_symlinks=False)
            promoted_identity = _identity(metadata)
        return _JournalEntry(operation, locked, transaction, promoted_identity, desired_raw)
    except ApplyError:
        raise
    except OSError as error:
        raise ApplyError(
            f"cannot promote managed link {locked.target.root / Path(operation.relative_path)}: {_bounded(error)}"
        ) from error
    finally:
        for descriptor in (staged_parent, backup_parent, final_parent):
            if descriptor >= 0:
                os.close(descriptor)


def _rollback_entry(entry: _JournalEntry) -> None:
    final_parent = _open_parent_at(
        entry.locked.root_fd, entry.operation.relative_path, create=False
    )
    backup_parent = -1
    name = entry.operation.relative_path.name
    try:
        if entry.operation.action in {"CREATE", "REPLACE"} and _exists_at(final_parent, name):
            metadata = os.stat(name, dir_fd=final_parent, follow_symlinks=False)
            raw = os.readlink(name, dir_fd=final_parent) if stat.S_ISLNK(metadata.st_mode) else None
            if (
                not stat.S_ISLNK(metadata.st_mode)
                or _identity(metadata) != entry.promoted_identity
                or raw != entry.desired_raw_target
            ):
                raise OSError(
                    f"refusing to delete changed destination during rollback: "
                    f"{entry.locked.target.root / Path(entry.operation.relative_path)}"
                )
            os.unlink(name, dir_fd=final_parent)
        if entry.operation.action in {"REPLACE", "REMOVE"}:
            backup_parent = _open_parent_at(
                entry.transaction.backup_fd, entry.operation.relative_path, create=False
            )
            if _exists_at(backup_parent, name):
                if _exists_at(final_parent, name):
                    raise OSError(f"rollback destination is occupied: {name}")
                os.replace(name, name, src_dir_fd=backup_parent, dst_dir_fd=final_parent)
    finally:
        if backup_parent >= 0:
            os.close(backup_parent)
        os.close(final_parent)


def _restore_metadata(locked: _LockedTarget) -> None:
    if locked.previous_managed is None:
        try:
            os.unlink("managed.json", dir_fd=locked.namespace_fd)
        except FileNotFoundError:
            pass
    else:
        _atomic_write_at(locked.namespace_fd, "managed.json", locked.previous_managed)


def _remove_contents(directory_fd: int) -> None:
    # os.listdir(fd) shares the open file description's directory offset with
    # descriptors duplicated while traversing. Re-open through procfs so every
    # pass has an independent offset while remaining anchored to this inode.
    while names := os.listdir(f"/proc/self/fd/{directory_fd}"):
        for name in names:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
                child_fd = os.open(name, _DIR_FLAGS, dir_fd=directory_fd)
                try:
                    _remove_contents(child_fd)
                finally:
                    os.close(child_fd)
                os.rmdir(name, dir_fd=directory_fd)
            else:
                os.unlink(name, dir_fd=directory_fd)


def _remove_transaction_tree(transaction: _TransactionDirs, kind: str) -> None:
    if kind == "staging":
        if transaction.staging_removed:
            return
        _remove_contents(transaction.staging_fd)
        os.rmdir(transaction.token, dir_fd=transaction.staging_parent_fd)
        os.close(transaction.staging_fd)
        transaction.staging_fd = -1
        transaction.staging_removed = True
    else:
        if transaction.backup_removed:
            return
        _remove_contents(transaction.backup_fd)
        os.rmdir(transaction.token, dir_fd=transaction.backup_parent_fd)
        os.close(transaction.backup_fd)
        transaction.backup_fd = -1
        transaction.backup_removed = True


def _remove_empty_transaction_parents(locked: _LockedTarget) -> None:
    transaction = locked.transaction
    if transaction is None:
        return
    for name, descriptor, created in (
        ("staging", transaction.staging_parent_fd, transaction.staging_parent_created),
        ("backup", transaction.backup_parent_fd, transaction.backup_parent_created),
    ):
        removed = transaction.staging_removed if name == "staging" else transaction.backup_removed
        if descriptor >= 0 and removed:
            os.close(descriptor)
            if name == "staging":
                transaction.staging_parent_fd = -1
            else:
                transaction.backup_parent_fd = -1
        if created:
            try:
                os.rmdir(name, dir_fd=locked.namespace_fd)
            except OSError:
                pass


def _remove_created_parents(created: list[_CreatedParent], errors: list[str]) -> None:
    seen: set[tuple[str, PurePosixPath]] = set()
    for item in reversed(created):
        key = (item.locked.target.id, item.relative)
        if key in seen:
            continue
        seen.add(key)
        parent_relative = item.relative.parent / "sentinel"
        parent_fd = -1
        try:
            if item.relative.parent == PurePosixPath("."):
                parent_fd = os.dup(item.locked.root_fd)
            else:
                parent_fd = _open_parent_at(item.locked.root_fd, parent_relative, create=False)
            os.rmdir(item.relative.name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(_bounded(error))
        finally:
            if parent_fd >= 0:
                os.close(parent_fd)


def _failure_receipt_at(
    locked: _LockedTarget, phase: str, error: BaseException, rollback: list[str]
) -> None:
    document = {
        "status": "failed",
        "phase": _bounded(phase),
        "error": _bounded(error),
        "rollback_errors": [_bounded(item) for item in rollback[:10]],
    }
    payload = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    _atomic_write_at(locked.namespace_fd, "failure.json", payload)


def _cleanup_initially_absent(locked: _LockedTarget, errors: list[str]) -> None:
    transaction = locked.transaction
    if transaction is not None:
        for kind in ("staging", "backup"):
            try:
                _remove_transaction_tree(transaction, kind)
            except OSError as error:
                errors.append(_bounded(error))
        _remove_empty_transaction_parents(locked)
    for name in ("failure.json", "managed.json", "operation.lock"):
        try:
            os.unlink(name, dir_fd=locked.namespace_fd)
        except FileNotFoundError:
            pass
        except OSError as error:
            errors.append(_bounded(error))
    try:
        os.rmdir(".skill-delegator", dir_fd=locked.root_fd)
    except OSError as error:
        errors.append(_bounded(error))
    _remove_created_chain(locked.created_chain, errors)


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
    """Apply one immutable reviewed plan under stable inode locks and directory descriptors."""

    if not math.isfinite(lock_timeout) or lock_timeout < 0:
        raise ApplyError("lock_timeout must be finite non-negative")
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
    locked_targets: list[_LockedTarget] = []
    journals: list[_JournalEntry] = []
    created_parents: list[_CreatedParent] = []
    rollback_errors: list[str] = []
    cleanup_errors: list[str] = []
    phase = "locking"
    committed = False
    token = uuid.uuid4().hex
    try:
        deadline = time.monotonic() + lock_timeout
        for target in sorted(plan.targets, key=lambda item: (str(item.root), item.id)):
            locked = _prepare_lock(target, deadline=deadline)
            locked_targets.append(locked)
            _initialize_metadata(locked)
        _checkpoint("after-lock")
        _verify_all(locked_targets)

        phase = "fresh-state validation"
        for locked in locked_targets:
            if _fresh_fingerprint(locked) != locked.target.current_fingerprint:
                raise ApplyError(f"stale plan for target {locked.target.id}; current state changed")
        _checkpoint("after-scan")
        _verify_all(locked_targets)

        phase = "staging"
        for locked in locked_targets:
            transaction = _make_transaction(locked, token)
            _stage(locked, transaction)
        _checkpoint("after-stage")
        _verify_all(locked_targets)

        phase = "promotion"
        locked_by_id = {locked.target.id: locked for locked in locked_targets}
        for promoted, operation in enumerate(mutations, start=1):
            locked = locked_by_id[operation.target_id]
            if locked.transaction is None:
                raise ApplyError("internal transaction directory binding is missing")
            journal = _promote(locked, operation, locked.transaction, created_parents)
            journals.append(journal)
            _checkpoint(f"after-promote-{promoted}")
            _verify_all(locked_targets)

        phase = "pre-commit staging cleanup"
        for locked in locked_targets:
            if locked.transaction is not None:
                _remove_transaction_tree(locked.transaction, "staging")
        _verify_all(locked_targets)

        phase = "metadata publication"
        _checkpoint("before-metadata")
        _verify_all(locked_targets)
        for index, locked in enumerate(locked_targets, start=1):
            _atomic_write_at(locked.namespace_fd, "managed.json", _canonical_managed(locked.target))
            _checkpoint(f"after-metadata-{index}")
            _verify_all(locked_targets)
        committed = True
        phase = "post-commit cleanup"
        _checkpoint("after-metadata")

        for index, locked in enumerate(locked_targets, start=1):
            if locked.transaction is not None:
                _remove_transaction_tree(locked.transaction, "backup")
                _checkpoint(f"after-backup-cleanup-{index}")
        for locked in locked_targets:
            _remove_empty_transaction_parents(locked)
        return ApplyResult(len(mutations), len(locked_targets))
    except Exception as error:
        phase_at_failure = phase
        if committed:
            for locked in locked_targets:
                transaction = locked.transaction
                if transaction is not None:
                    for kind in ("staging", "backup"):
                        try:
                            _remove_transaction_tree(transaction, kind)
                        except OSError as cleanup_error:
                            cleanup_errors.append(_bounded(cleanup_error))
                    _remove_empty_transaction_parents(locked)
                if not locked.initially_absent:
                    try:
                        _failure_receipt_at(locked, phase_at_failure, error, cleanup_errors)
                    except OSError as receipt_error:
                        cleanup_errors.append(f"failure receipt: {_bounded(receipt_error)}")
            suffix = (
                f"; residual cleanup: {'; '.join(cleanup_errors[:10])}" if cleanup_errors else ""
            )
            raise ApplyError(
                f"transaction committed; cleanup failed during {phase_at_failure}: "
                f"{_bounded(error)}{suffix}"
            ) from error

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
        for locked in locked_targets:
            transaction = locked.transaction
            if transaction is not None:
                try:
                    _remove_transaction_tree(transaction, "staging")
                except OSError as rollback_error:
                    rollback_errors.append(_bounded(rollback_error))
                if not rollback_errors:
                    try:
                        _remove_transaction_tree(transaction, "backup")
                    except OSError as rollback_error:
                        rollback_errors.append(_bounded(rollback_error))
                _remove_empty_transaction_parents(locked)
        _remove_created_parents(created_parents, rollback_errors)
        for locked in locked_targets:
            if locked.initially_absent:
                _cleanup_initially_absent(locked, rollback_errors)
            else:
                try:
                    _failure_receipt_at(locked, phase_at_failure, error, rollback_errors)
                except OSError as receipt_error:
                    rollback_errors.append(f"failure receipt: {_bounded(receipt_error)}")
        suffix = f"; rollback failed: {'; '.join(rollback_errors[:10])}" if rollback_errors else ""
        if isinstance(error, ApplyError):
            raise ApplyError(f"{_bounded(error)}{suffix}") from error
        raise ApplyError(
            f"apply failed during {phase_at_failure}: {_bounded(error)}{suffix}"
        ) from error
    finally:
        for locked in reversed(locked_targets):
            _close_locked(locked)
