"""Canonical, digest-bound reconciliation plan artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Any

from skill_delegator.errors import SourceError
from skill_delegator.inventory import hash_tree
from skill_delegator.models import AuthorityConfig, DesiredState, ReconciliationPlan
from skill_delegator.planner import plan_document
from skill_delegator.safe_paths import open_existing_anchored_directory
from skill_delegator.schema_validation import schema_error_location, schema_errors

_MAX_PLAN_BYTES = 16 * 1024 * 1024
_FILE_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)


class ExactPlanError(RuntimeError):
    """An exact plan artifact cannot be safely created or consumed."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_locked_sources(desired: DesiredState) -> None:
    """Require each complete cached source snapshot to retain its locked identity."""

    for source in desired.sources:
        try:
            actual = hash_tree(source.root)
        except (OSError, SourceError) as error:
            raise ExactPlanError("locked source snapshot is unavailable or unsafe") from error
        if actual != source.tree_hash:
            raise ExactPlanError("locked source snapshot differs from reviewed lock")


def artifact_document(
    config: AuthorityConfig, target_scope: str | None, plan: ReconciliationPlan
) -> dict[str, object]:
    """Build the allow-listed exact-plan document from one carried config snapshot."""

    if config.input_snapshot is None:
        raise ExactPlanError("configuration snapshot unavailable")
    config_inputs = [
        {"name": item.name, "sha256": _sha256(item.data)} for item in config.input_snapshot.inputs
    ]
    lock_sha256 = next(
        item["sha256"] for item in config_inputs if item["name"] == "skill-lock.yaml"
    )
    if plan.blocked:
        change_state = "blocked"
    elif plan.has_changes:
        change_state = "changes"
    else:
        change_state = "converged"
    return {
        "schema_version": 1,
        "authority_id": config.authority_id,
        "target_scope": target_scope,
        "config_inputs": config_inputs,
        "lock_sha256": lock_sha256,
        "target_fingerprints": [
            {"target_id": target.id, "sha256": target.current_fingerprint}
            for target in plan.targets
        ],
        "operations": plan_document(plan)["operations"],
        "blocked": list(plan.blocked),
        "change_state": change_state,
    }


def canonical_artifact_bytes(document: dict[str, object]) -> bytes:
    """Validate and serialize an exact plan with one canonical terminal newline."""

    errors = schema_errors(document, "exact-plan.schema.json")
    if errors:
        error = errors[0]
        raise ExactPlanError(
            f"plan artifact violates schema at {schema_error_location(error)} ({error.validator})"
        )
    names = [item["name"] for item in document["config_inputs"]]  # type: ignore[index]
    target_ids = [item["target_id"] for item in document["target_fingerprints"]]  # type: ignore[index]
    if len(names) != len(set(names)) or names != sorted(names, key=os.fsencode):
        raise ExactPlanError("plan artifact has invalid config input identities")
    if len(target_ids) != len(set(target_ids)) or target_ids != sorted(target_ids):
        raise ExactPlanError("plan artifact has invalid target fingerprint identities")
    lock_hash = next(
        (item["sha256"] for item in document["config_inputs"] if item["name"] == "skill-lock.yaml"),  # type: ignore[index]
        None,
    )
    if lock_hash != document["lock_sha256"]:
        raise ExactPlanError("plan artifact has incoherent lock identity")
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def build_artifact(
    config: AuthorityConfig, target_scope: str | None, plan: ReconciliationPlan
) -> tuple[bytes, str]:
    payload = canonical_artifact_bytes(artifact_document(config, target_scope, plan))
    return payload, _sha256(payload)


def _open_parent(path: Path):
    try:
        return open_existing_anchored_directory(path.parent, description="plan-path")
    except SourceError as error:
        raise ExactPlanError("plan path has an unsafe or missing parent") from error


def publish_artifact(path: Path, payload: bytes) -> None:
    """Atomically publish a new artifact without following or replacing any pathname."""

    lexical = Path(os.path.abspath(path))
    if lexical.name in {"", ".", ".."}:
        raise ExactPlanError("plan output path is invalid")
    with _open_parent(lexical) as parent:
        temporary = f".{lexical.name}.{secrets.token_hex(12)}.tmp"
        descriptor = -1
        published = False
        primary: ExactPlanError | None = None
        try:
            parent.verify(description="plan-path")
            try:
                os.stat(lexical.name, dir_fd=parent.fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ExactPlanError("plan output already exists")
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(temporary, flags, 0o600, dir_fd=parent.fd)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = -1
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            parent.verify(description="plan-path")
            os.link(
                temporary,
                lexical.name,
                src_dir_fd=parent.fd,
                dst_dir_fd=parent.fd,
                follow_symlinks=False,
            )
            published = True
            os.fsync(parent.fd)
            parent.verify(description="plan-path")
        except ExactPlanError as error:
            primary = error
        except (OSError, SourceError) as error:
            primary = ExactPlanError("cannot atomically publish plan artifact")
            primary.__cause__ = error
        finally:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    primary = primary or ExactPlanError("cannot close plan publication file")
            try:
                os.unlink(temporary, dir_fd=parent.fd)
            except FileNotFoundError:
                pass
            except OSError as error:
                primary = primary or ExactPlanError("cannot clean up plan publication")
                primary.__cause__ = error
            if primary is not None and published:
                try:
                    os.unlink(lexical.name, dir_fd=parent.fd)
                    os.fsync(parent.fd)
                except OSError as error:
                    raise ExactPlanError("cannot roll back failed plan publication") from error
        if primary is not None:
            raise primary


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ExactPlanError("plan artifact contains duplicate JSON fields")
        document[key] = value
    return document


def read_artifact(path: Path, expected_sha256: str) -> tuple[dict[str, object], bytes]:
    """Read, digest-check, strictly parse, and validate one canonical artifact."""

    if len(expected_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha256
    ):
        raise ExactPlanError("expected plan SHA-256 must be 64 lowercase hexadecimal characters")
    lexical = Path(os.path.abspath(path))
    with _open_parent(lexical) as parent:
        descriptor = -1
        try:
            parent.verify(description="plan-path")
            descriptor = os.open(lexical.name, _FILE_FLAGS, dir_fd=parent.fd)
            opened = os.fstat(descriptor)
            lexical_stat = os.stat(lexical.name, dir_fd=parent.fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(opened.st_mode)
                or not stat.S_ISREG(lexical_stat.st_mode)
                or (opened.st_dev, opened.st_ino) != (lexical_stat.st_dev, lexical_stat.st_ino)
                or opened.st_size > _MAX_PLAN_BYTES
            ):
                raise ExactPlanError("plan input must be a bounded regular file")
            chunks: list[bytes] = []
            remaining = _MAX_PLAN_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            after = os.fstat(descriptor)
            lexical_after = os.stat(lexical.name, dir_fd=parent.fd, follow_symlinks=False)
            parent.verify(description="plan-path")
            expected_identity = (opened.st_dev, opened.st_ino)
            if (
                len(payload) > _MAX_PLAN_BYTES
                or (after.st_dev, after.st_ino) != expected_identity
                or (lexical_after.st_dev, lexical_after.st_ino) != expected_identity
                or not stat.S_ISREG(after.st_mode)
                or not stat.S_ISREG(lexical_after.st_mode)
                or after.st_size != opened.st_size
                or after.st_mtime_ns != opened.st_mtime_ns
            ):
                raise ExactPlanError("plan input changed while being read")
        except ExactPlanError:
            raise
        except (OSError, SourceError) as error:
            raise ExactPlanError("plan input is unavailable or unsafe") from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    if _sha256(payload) != expected_sha256:
        raise ExactPlanError("plan SHA-256 does not match artifact bytes")
    try:
        document = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except ExactPlanError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExactPlanError("plan artifact is not valid JSON") from error
    if not isinstance(document, dict):
        raise ExactPlanError("plan artifact must be a JSON object")
    canonical = canonical_artifact_bytes(document)
    if canonical != payload:
        raise ExactPlanError("plan artifact bytes are not canonical")
    return document, payload
