"""Build and atomically serialize exact source locks."""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path, PurePosixPath

import yaml

from skill_delegator.errors import SourceError
from skill_delegator.models import (
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
            tree_hash = None
        elif resolved.source_type == "filesystem":
            resolved_commit = None
            tree_hash = resolved.revision
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
    return SkillLock(schema_version=1, sources=tuple(locked_sources))


def _document(lock: SkillLock) -> dict[str, object]:
    return {
        "schema_version": lock.schema_version,
        "sources": [
            {
                "source_id": source.source_id,
                "type": source.source_type,
                **(
                    {"resolved_commit": source.resolved_commit}
                    if source.resolved_commit is not None
                    else {"tree_hash": source.tree_hash}
                ),
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


def _rollback_publication(
    parent: AnchoredDirectory,
    name: str,
    backup: str | None,
    published_identity: tuple[int, int],
) -> None:
    try:
        current = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
    except OSError as error:
        raise SourceError("lock-rollback-unsafe") from error
    if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != published_identity:
        raise SourceError("lock-rollback-unsafe")
    try:
        if backup is None:
            os.unlink(name, dir_fd=parent.fd)
        else:
            os.replace(backup, name, src_dir_fd=parent.fd, dst_dir_fd=parent.fd)
        os.fsync(parent.fd)
    except OSError as error:
        raise SourceError("lock-publication-failed") from error


def write_lock_atomic(path: Path, lock: SkillLock) -> None:
    """Publish canonical lock bytes, rolling back every reported publication failure."""

    payload = serialize_lock(lock)
    parent = open_anchored_directory(path.parent, description="lock-parent")
    stage: str | None = None
    backup: str | None = None
    published_identity: tuple[int, int] | None = None
    committed = False
    try:
        existing = _read_file_at(parent, path.name)
        if existing is not None and existing[0] == payload:
            return
        mode = stat.S_IMODE(existing[1].st_mode) if existing is not None else 0o644
        stage = _unique_name(f"{path.name}.stage")
        stage_fd = os.open(
            stage,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
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
            os.fsync(stage_fd)
            staged = os.fstat(stage_fd)
            if not stat.S_ISREG(staged.st_mode):
                raise OSError("staged lock is not regular")
        finally:
            os.close(stage_fd)
        os.chmod(stage, mode, dir_fd=parent.fd, follow_symlinks=False)
        parent.verify(description="lock-parent")

        if existing is not None:
            backup = _unique_name(f"{path.name}.backup")
            os.link(
                path.name,
                backup,
                src_dir_fd=parent.fd,
                dst_dir_fd=parent.fd,
                follow_symlinks=False,
            )
            current = os.stat(path.name, dir_fd=parent.fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (existing[1].st_dev, existing[1].st_ino):
                raise OSError("lock changed before publication")

        os.replace(stage, path.name, src_dir_fd=parent.fd, dst_dir_fd=parent.fd)
        stage = None
        published_identity = (staged.st_dev, staged.st_ino)
        published = os.stat(path.name, dir_fd=parent.fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(published.st_mode)
            or (published.st_dev, published.st_ino) != published_identity
        ):
            raise SourceError("lock-rollback-unsafe")
        os.fsync(parent.fd)
        parent.verify(description="lock-parent")
        committed = True
    except SourceError:
        if published_identity is not None:
            _rollback_publication(parent, path.name, backup, published_identity)
            backup = None
        raise
    except OSError as error:
        if published_identity is not None:
            try:
                _rollback_publication(parent, path.name, backup, published_identity)
                backup = None
            except SourceError as rollback_error:
                raise rollback_error from error
        raise SourceError("lock-publication-failed") from error
    finally:
        if stage is not None:
            try:
                os.unlink(stage, dir_fd=parent.fd)
            except OSError:
                pass
        if backup is not None and (committed or published_identity is None):
            # Publication is durable (or never happened). Cleanup failure must
            # not create a contradictory reported failure. On unsafe rollback,
            # retain the backup as a recovery journal.
            try:
                os.unlink(backup, dir_fd=parent.fd)
                os.fsync(parent.fd)
            except OSError:
                pass
        parent.close()
