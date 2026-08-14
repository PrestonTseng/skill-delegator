"""Build and atomically serialize exact source locks."""

from __future__ import annotations

import os
import tempfile
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
            expected_prefix = f"{source_id}/"
            if not skill.canonical_id.startswith(expected_prefix):
                raise SourceError(
                    f"skill has incorrect canonical source identity: {skill.canonical_id}"
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


def write_lock_atomic(path: Path, lock: SkillLock) -> None:
    """Atomically replace ``path`` with canonical lock bytes.

    An identical existing file is left untouched, avoiding needless metadata and
    Git worktree churn on repeated lock generation.
    """

    payload = serialize_lock(lock)
    try:
        if path.read_bytes() == payload:
            return
    except FileNotFoundError:
        pass
    except OSError as error:
        raise SourceError(f"cannot read existing lock {path}: {error}") from error

    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o644
    try:
        mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        pass
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
        temporary_name = None
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as error:
        raise SourceError(f"cannot atomically write lock {path}: {error}") from error
    finally:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
