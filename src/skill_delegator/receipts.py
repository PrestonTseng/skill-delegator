"""Canonical audit receipts with descriptor-anchored content-addressed publication."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Any

from skill_delegator.models import VerificationResult
from skill_delegator.schema_validation import schema_error_location, schema_errors

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
if hasattr(os, "O_NOFOLLOW"):
    _DIR_FLAGS |= os.O_NOFOLLOW


class ReceiptError(RuntimeError):
    """A receipt cannot be validated or safely published."""


_CONFIG_NAMES = (
    "authority.yaml",
    "delegations.yaml",
    "pool.yaml",
    "skill-lock.yaml",
    "sources.yaml",
)


def _validate_semantics(result: VerificationResult) -> None:
    if tuple(sorted(item.name for item in result.config_hashes)) != _CONFIG_NAMES:
        raise ReceiptError("verification result has invalid config_hashes identities")
    source_ids = [item.source_id for item in result.locked_sources]
    if len(source_ids) != len(set(source_ids)):
        raise ReceiptError("verification result has duplicate locked_sources identities")
    for item in result.locked_sources:
        is_git = (
            item.source_type == "git"
            and item.revision_kind == "resolved_commit"
            and item.tree_identity is None
            and len(item.revision) in range(40, 65)
        )
        is_filesystem = (
            item.source_type == "filesystem"
            and item.revision_kind == "tree_hash"
            and len(item.revision) == 64
            and item.tree_identity == item.revision
        )
        if not (is_git or is_filesystem):
            raise ReceiptError("verification result has incoherent locked_sources identity")
    summary = result.operation_summary
    drift_count = sum(reason.category == "drift" for reason in result.reasons)
    invalid_count = sum(reason.category == "invalid" for reason in result.reasons)
    expected_result = "invalid" if invalid_count else "drift" if drift_count else "converged"
    if (
        summary.verified_links > summary.desired_links
        or summary.drift_count != drift_count
        or summary.invalid_count != invalid_count
        or result.result != expected_result
        or len(result.reasons) != len(set(result.reasons))
    ):
        raise ReceiptError("verification result has incoherent operation evidence")


def receipt_document(result: VerificationResult) -> dict[str, Any]:
    """Render only allow-listed, deterministic verification evidence."""

    return {
        "schema_version": 1,
        "authority_id": result.authority_id,
        "repository": {
            "available": result.repository_commit_available,
            "commit": result.repository_commit,
        },
        "config_hashes": [
            {"name": item.name, "sha256": item.sha256}
            for item in sorted(result.config_hashes, key=lambda item: item.name)
        ],
        "locked_sources": [
            {
                "source_id": item.source_id,
                "type": item.source_type,
                "revision_kind": item.revision_kind,
                "revision": item.revision,
                "tree_identity": item.tree_identity,
            }
            for item in sorted(result.locked_sources, key=lambda item: item.source_id)
        ],
        "operation_summary": {
            "desired_targets": result.operation_summary.desired_targets,
            "desired_links": result.operation_summary.desired_links,
            "verified_links": result.operation_summary.verified_links,
            "drift_count": result.operation_summary.drift_count,
            "invalid_count": result.operation_summary.invalid_count,
        },
        "result": result.result,
        "reasons": [
            {
                "code": item.code,
                "category": item.category,
                "target_id": item.target_id,
                "artifact_id": item.artifact_id,
                "detail": item.detail,
            }
            for item in result.reasons
        ],
        "target_fingerprints": [
            {"target_id": item.target_id, "sha256": item.sha256}
            for item in result.target_fingerprints
        ],
    }


def _payload(result: VerificationResult) -> bytes:
    document = receipt_document(result)
    errors = schema_errors(document, "verification-receipt.schema.json")
    if errors:
        error = errors[0]
        raise ReceiptError(
            "verification result violates receipt schema at "
            f"{schema_error_location(error)} ({error.validator})"
        )
    _validate_semantics(result)
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _open_receipt_root(receipt_root: Path) -> int:
    root = Path(os.path.abspath(receipt_root))
    if len(root.parts) < 3 or root.parts[-2:] != ("var", "receipts"):
        raise ReceiptError("receipt root must be the lexical var/receipts directory")
    try:
        descriptor = os.open(root.anchor, _DIR_FLAGS)
    except OSError as error:
        raise ReceiptError("cannot open receipt root anchor") from error
    try:
        for part in root.parts[1:]:
            try:
                next_descriptor = os.open(part, _DIR_FLAGS, dir_fd=descriptor)
            except FileNotFoundError:
                try:
                    os.mkdir(part, 0o700, dir_fd=descriptor)
                except OSError as error:
                    raise ReceiptError("cannot create safe receipt directory") from error
                try:
                    os.fsync(descriptor)
                except OSError as error:
                    raise ReceiptError("cannot sync created receipt ancestor") from error
                try:
                    next_descriptor = os.open(part, _DIR_FLAGS, dir_fd=descriptor)
                except OSError as error:
                    raise ReceiptError("cannot open created receipt directory") from error
            except OSError as error:
                raise ReceiptError(
                    "receipt root has a symlinked or non-directory component"
                ) from error
            try:
                os.close(descriptor)
            except OSError as error:
                try:
                    os.close(next_descriptor)
                except OSError:
                    pass
                raise ReceiptError("cannot close receipt ancestor") from error
            descriptor = next_descriptor
        return descriptor
    except Exception as error:
        try:
            os.close(descriptor)
        except OSError as close_error:
            if not isinstance(error, ReceiptError):
                raise ReceiptError("cannot close receipt traversal descriptor") from close_error
        raise


def _verify_root_identity(root: Path, directory_fd: int) -> None:
    try:
        lexical = root.lstat()
        opened = os.fstat(directory_fd)
    except OSError as error:
        raise ReceiptError("receipt root identity changed during publication") from error
    if not stat.S_ISDIR(lexical.st_mode) or (lexical.st_dev, lexical.st_ino) != (
        opened.st_dev,
        opened.st_ino,
    ):
        raise ReceiptError("receipt root identity changed during publication")


def _existing_payload(directory_fd: int, name: str) -> bytes | None:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ReceiptError("receipt content address is unsafe") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ReceiptError("receipt content address is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    except ReceiptError:
        raise
    except OSError as error:
        raise ReceiptError("cannot read existing receipt content address") from error
    finally:
        try:
            os.close(descriptor)
        except OSError as error:
            raise ReceiptError("cannot close existing receipt descriptor") from error


def write_receipt(result: VerificationResult, receipt_root: Path) -> Path:
    """Atomically publish a canonical receipt without overwrite or collision."""

    payload = _payload(result)
    content_hash = hashlib.sha256(payload).hexdigest()
    name = f"{content_hash}.json"
    root = Path(os.path.abspath(receipt_root))
    directory_fd = _open_receipt_root(root)
    temporary = f".{content_hash}.{secrets.token_hex(12)}.tmp"
    descriptor = -1
    published = False
    try:
        _verify_root_identity(root, directory_fd)
        existing = _existing_payload(directory_fd, name)
        if existing is not None:
            if existing != payload:
                raise ReceiptError("receipt content-address collision; refusing overwrite")
            _verify_root_identity(root, directory_fd)
            return root / name
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(
                temporary,
                name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
            published = True
        except FileExistsError:
            existing = _existing_payload(directory_fd, name)
            if existing != payload:
                raise ReceiptError("receipt content-address collision; refusing overwrite")
        os.fsync(directory_fd)
        _verify_root_identity(root, directory_fd)
        return root / name
    except ReceiptError:
        if published:
            try:
                os.unlink(name, dir_fd=directory_fd)
                os.fsync(directory_fd)
            except OSError:
                pass
        raise
    except OSError as error:
        if published:
            try:
                os.unlink(name, dir_fd=directory_fd)
                os.fsync(directory_fd)
            except OSError:
                pass
        raise ReceiptError("cannot atomically publish verification receipt") from error
    finally:
        cleanup_error: OSError | None = None
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError as error:
                cleanup_error = error
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        except OSError as error:
            cleanup_error = cleanup_error or error
        try:
            os.close(directory_fd)
        except OSError as error:
            cleanup_error = cleanup_error or error
        if cleanup_error is not None:
            raise ReceiptError("cannot clean up receipt publication descriptors") from cleanup_error
