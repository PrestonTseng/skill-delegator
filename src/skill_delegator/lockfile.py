"""Build and atomically serialize exact source locks."""

from __future__ import annotations

import os
import secrets
import stat
from enum import Enum
from pathlib import Path, PurePosixPath

import yaml

from skill_delegator.errors import SourceError
from skill_delegator.models import (
    PORTABLE_HASH_ALGORITHM,
    AuthorityConfig,
    LockedSkill,
    LockedSource,
    ResolvedSource,
    SkillLock,
)
from skill_delegator.safe_paths import AnchoredDirectory, open_anchored_directory


def build_lock(config: AuthorityConfig, resolved_sources: tuple[ResolvedSource, ...]) -> SkillLock:
    """Build a complete exact lock in memory and validate all pool references."""

    specs = {source.id: source for source in config.sources}
    if len(specs) != len(config.sources):
        raise SourceError("duplicate configured source id")
    resolved_by_id: dict[str, ResolvedSource] = {}
    for source in resolved_sources:
        if source.source_id in resolved_by_id:
            raise SourceError(f"duplicate resolved source id: {source.source_id}")
        resolved_by_id[source.source_id] = source
    missing_sources = set(specs) - set(resolved_by_id)
    extra_sources = set(resolved_by_id) - set(specs)
    if missing_sources or extra_sources:
        raise SourceError(
            "resolved source set differs from configuration: "
            f"missing={sorted(missing_sources)}, extra={sorted(extra_sources)}"
        )

    locked_sources: list[LockedSource] = []
    all_canonical_ids: set[str] = set()
    for source_id in sorted(resolved_by_id):
        resolved = resolved_by_id[source_id]
        spec = specs[source_id]
        locked_skills: list[LockedSkill] = []
        for skill in sorted(resolved.skills, key=lambda item: item.canonical_id):
            if skill.canonical_id in all_canonical_ids:
                raise SourceError(f"duplicate canonical artifact id: {skill.canonical_id}")
            expected_canonical_id = f"{source_id}/{skill.relative_path.as_posix()}"
            if skill.canonical_id != expected_canonical_id:
                raise SourceError(
                    "skill canonical identity does not match its relative path: "
                    f"expected {expected_canonical_id}, got {skill.canonical_id}"
                )
            all_canonical_ids.add(skill.canonical_id)
            source_path = PurePosixPath(*spec.skill_root.parts, *skill.relative_path.parts)
            locked_skills.append(
                LockedSkill(
                    canonical_id=skill.canonical_id,
                    runtime_name=skill.runtime_name,
                    path=source_path,
                    sha256=skill.sha256,
                )
            )
        if resolved.source_type == "git":
            resolved_commit = resolved.revision
            tree_hash = resolved.tree_hash
        elif resolved.source_type == "filesystem":
            resolved_commit = None
            tree_hash = resolved.tree_hash
        else:
            raise SourceError(f"unsupported resolved source type: {resolved.source_type}")
        locked_sources.append(
            LockedSource(
                source_id=source_id,
                source_type=resolved.source_type,
                resolved_commit=resolved_commit,
                tree_hash=tree_hash,
                skills=tuple(locked_skills),
            )
        )

    missing_references = sorted(
        item.canonical_id for item in config.pool if item.canonical_id not in all_canonical_ids
    )
    if missing_references:
        raise SourceError(f"missing locked skill reference: {', '.join(missing_references)}")
    return SkillLock(
        schema_version=2,
        sources=tuple(locked_sources),
        hash_algorithm=PORTABLE_HASH_ALGORITHM,
    )


def _document(lock: SkillLock) -> dict[str, object]:
    return {
        "schema_version": lock.schema_version,
        **({"hash_algorithm": lock.hash_algorithm} if lock.schema_version >= 2 else {}),
        "sources": [
            {
                "source_id": source.source_id,
                "type": source.source_type,
                **({"resolved_commit": source.resolved_commit} if source.resolved_commit else {}),
                "tree_hash": source.tree_hash,
                "skills": [
                    {
                        "canonical_id": skill.canonical_id,
                        "runtime_name": skill.runtime_name,
                        "path": skill.path.as_posix(),
                        "sha256": skill.sha256,
                    }
                    for skill in source.skills
                ],
            }
            for source in lock.sources
        ],
    }


def serialize_lock(lock: SkillLock) -> bytes:
    """Return canonical UTF-8 YAML bytes for a lock."""

    text = yaml.safe_dump(
        _document(lock),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    return text.encode("utf-8")


def _read_file_at(parent: AnchoredDirectory, name: str) -> tuple[bytes, os.stat_result] | None:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=parent.fd)
    except FileNotFoundError:
        return None
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError("lock is not a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
        return b"".join(chunks), metadata
    finally:
        os.close(fd)


def _unique_name(prefix: str) -> str:
    return f".{prefix}-{secrets.token_hex(12)}"


class _PublicOutcome(Enum):
    CANDIDATE = "candidate"
    UNSAFE = "unsafe"


def _observe_public_outcome(
    parent: AnchoredDirectory,
    name: str,
    candidate_identity: tuple[int, int],
    candidate_payload: bytes,
) -> _PublicOutcome:
    """Classify a committed publication without mutating its public pathname."""

    try:
        current = _read_file_at(parent, name)
        if current is None:
            return _PublicOutcome.UNSAFE
        public = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
    except OSError:
        return _PublicOutcome.UNSAFE

    opened_identity = (current[1].st_dev, current[1].st_ino)
    if not stat.S_ISREG(public.st_mode) or (public.st_dev, public.st_ino) != opened_identity:
        return _PublicOutcome.UNSAFE
    if opened_identity == candidate_identity:
        return (
            _PublicOutcome.CANDIDATE if current[0] == candidate_payload else _PublicOutcome.UNSAFE
        )
    return _PublicOutcome.UNSAFE


def _verify_public_snapshot(
    parent: AnchoredDirectory, name: str, expected: tuple[bytes, os.stat_result] | None
) -> None:
    """Fail before publication if the public lock differs from its initial snapshot."""

    current = _read_file_at(parent, name)
    if expected is None:
        if current is not None:
            raise OSError("lock appeared before publication")
        try:
            os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise OSError("unsafe lock appeared before publication")
    if current is None:
        raise OSError("lock disappeared before publication")
    public = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
    expected_identity = (expected[1].st_dev, expected[1].st_ino)
    opened_identity = (current[1].st_dev, current[1].st_ino)
    if (
        not stat.S_ISREG(public.st_mode)
        or opened_identity != expected_identity
        or (public.st_dev, public.st_ino) != expected_identity
        or current[0] != expected[0]
    ):
        raise OSError("lock changed before publication")


def write_lock_atomic(path: Path, lock: SkillLock) -> None:
    """Commit canonical bytes at atomic replace and never roll that pathname back."""

    payload = serialize_lock(lock)
    try:
        parent = open_anchored_directory(path.parent, description="lock-parent")
    except (SourceError, OSError) as error:
        raise SourceError("lock-publication-failed") from error
    stage: str | None = None
    published_identity: tuple[int, int] | None = None
    try:
        existing = _read_file_at(parent, path.name)
        if existing is not None and existing[0] == payload:
            return
        mode = stat.S_IMODE(existing[1].st_mode) if existing is not None else 0o644
        stage = _unique_name(f"{path.name}.stage")
        stage_fd = os.open(
            stage,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            mode,
            dir_fd=parent.fd,
        )
        try:
            view = memoryview(payload)
            while view:
                written = os.write(stage_fd, view)
                if written <= 0:
                    raise OSError("short lock write")
                view = view[written:]
            os.fchmod(stage_fd, mode)
            os.fsync(stage_fd)
            staged = os.fstat(stage_fd)
            if not stat.S_ISREG(staged.st_mode):
                raise OSError("staged lock is not regular")
            os.lseek(stage_fd, 0, os.SEEK_SET)
            staged_payload = b""
            while chunk := os.read(stage_fd, 65536):
                staged_payload += chunk
            if staged_payload != payload:
                raise OSError("staged lock differs from candidate")
        finally:
            os.close(stage_fd)
        parent.verify(description="lock-parent")
        staged_path = os.stat(stage, dir_fd=parent.fd, follow_symlinks=False)
        if (staged_path.st_dev, staged_path.st_ino) != (staged.st_dev, staged.st_ino):
            raise OSError("staged lock changed before publication")
        _verify_public_snapshot(parent, path.name, existing)

        os.replace(stage, path.name, src_dir_fd=parent.fd, dst_dir_fd=parent.fd)
        stage = None
        published_identity = (staged.st_dev, staged.st_ino)
        os.fsync(parent.fd)
        parent.verify(description="lock-parent")
    except (SourceError, OSError) as error:
        if published_identity is None:
            raise SourceError("lock-publication-failed") from error
        outcome = _observe_public_outcome(parent, path.name, published_identity, payload)
        if outcome is _PublicOutcome.CANDIDATE:
            return
        raise SourceError("lock-rollback-unsafe") from error
    finally:
        if stage is not None:
            try:
                os.unlink(stage, dir_fd=parent.fd)
            except OSError:
                pass
        parent.close()
