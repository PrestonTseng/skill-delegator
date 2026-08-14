"""Pure authority-bounded desired-state resolution."""

from __future__ import annotations

import os
import posixpath
import re
from pathlib import Path, PurePosixPath

from skill_delegator.identifiers import canonical_relative_path, is_canonical_id, is_source_id
from skill_delegator.models import (
    AuthorityConfig,
    DesiredLink,
    DesiredState,
    DesiredTarget,
    LockedSkill,
    SkillLock,
)


class ResolutionError(ValueError):
    """Desired state cannot be resolved without violating a boundary."""


_RUNTIME_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _duplicates(values: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _normalized_relative(path: PurePosixPath, *, label: str) -> PurePosixPath:
    if path.is_absolute():
        raise ResolutionError(f"{label} must be a confined relative path: {path}")
    normalized = PurePosixPath(posixpath.normpath(path.as_posix()))
    if normalized.parts and normalized.parts[0] == "..":
        raise ResolutionError(f"{label} must be a confined relative path: {path}")
    return normalized


def _canonical_suffix(source_id: str, canonical_id: str) -> PurePosixPath:
    if not is_source_id(source_id) or not is_canonical_id(canonical_id):
        raise ResolutionError(
            f"artifact {canonical_id} has invalid canonical source prefix or suffix"
        )
    prefix, separator, suffix = canonical_id.partition("/")
    if prefix != source_id:
        raise ResolutionError(f"artifact {canonical_id} is enclosed by source {source_id}")
    if separator != "/" or not suffix:
        raise ResolutionError(
            f"artifact {canonical_id} has invalid canonical source prefix or suffix"
        )
    relative = PurePosixPath(suffix)
    if not canonical_relative_path(relative):
        raise ResolutionError(
            f"artifact {canonical_id} has invalid canonical source prefix or suffix"
        )
    return relative


def _validate_locked_path(
    source_id: str, skill_root: PurePosixPath, skill: LockedSkill, suffix: PurePosixPath
) -> None:
    normalized_root = _normalized_relative(
        skill_root, label=f"configured skill root for source {source_id}"
    )
    try:
        normalized_path = _normalized_relative(skill.path, label=f"locked path {skill.path}")
    except ResolutionError as error:
        raise ResolutionError(
            f"locked path {skill.path} is outside configured skill root {skill_root}"
        ) from error
    if not normalized_path.is_relative_to(normalized_root) or normalized_path == normalized_root:
        raise ResolutionError(
            f"locked path {skill.path} is outside configured skill root {skill_root}"
        )
    try:
        relative = skill.path.relative_to(skill_root)
    except ValueError as error:
        raise ResolutionError(
            f"locked path {skill.path} is outside configured skill root {skill_root}"
        ) from error
    if relative != suffix:
        raise ResolutionError(f"locked path {skill.path} does not match canonical suffix {suffix}")


def _locked_skills(config: AuthorityConfig, lock: SkillLock) -> dict[str, LockedSkill]:
    configured = {source.id: source for source in config.sources}
    if len(configured) != len(config.sources):
        raise ResolutionError("duplicate configured source id")

    skills: dict[str, LockedSkill] = {}
    locked_source_ids: set[str] = set()
    for source in lock.sources:
        if source.source_id in locked_source_ids:
            raise ResolutionError(f"duplicate locked source id: {source.source_id}")
        locked_source_ids.add(source.source_id)

    missing = sorted(set(configured) - locked_source_ids)
    extra = sorted(locked_source_ids - set(configured))
    if missing or extra:
        raise ResolutionError(
            f"locked source set differs from configuration: missing={missing}, extra={extra}"
        )

    for source in lock.sources:
        spec = configured[source.source_id]
        if source.source_type != spec.type:
            raise ResolutionError(
                f"locked source {source.source_id} type {source.source_type!r} "
                f"does not match configured type {spec.type!r}"
            )
        for skill in source.skills:
            suffix = _canonical_suffix(source.source_id, skill.canonical_id)
            _validate_locked_path(source.source_id, spec.skill_root, skill, suffix)
            if _RUNTIME_NAME_PATTERN.fullmatch(skill.runtime_name) is None:
                raise ResolutionError(
                    f"locked artifact {skill.canonical_id} has an invalid runtime name"
                )
            if skill.canonical_id in skills:
                raise ResolutionError(f"duplicate locked artifact id: {skill.canonical_id}")
            skills[skill.canonical_id] = skill
    return skills


def _target_path(root: Path, artifact_id: str) -> Path:
    normalized_root = Path(os.path.abspath(root))
    candidate = Path(os.path.abspath(normalized_root.joinpath(*artifact_id.split("/"))))
    if not candidate.is_relative_to(normalized_root) or candidate == normalized_root:
        raise ResolutionError(
            f"artifact {artifact_id} resolves outside target root {normalized_root}"
        )
    return candidate


def resolve_desired_state(config: AuthorityConfig, lock: SkillLock) -> DesiredState:
    """Resolve immutable desired links without reading or mutating the filesystem."""

    pool_values = tuple(item.canonical_id for item in config.pool)
    duplicate_pool = _duplicates(pool_values)
    if duplicate_pool:
        raise ResolutionError(f"duplicate pool grant: {', '.join(duplicate_pool)}")
    pool = set(pool_values)
    locked = _locked_skills(config, lock)

    target_ids: set[str] = set()
    occupied_paths: dict[Path, tuple[str, str]] = {}
    desired_targets: list[DesiredTarget] = []
    for target in sorted(config.targets, key=lambda item: item.id):
        if target.id in target_ids:
            raise ResolutionError(f"duplicate target id: {target.id}")
        target_ids.add(target.id)

        duplicate_grants = _duplicates(target.grants)
        if duplicate_grants:
            raise ResolutionError(
                f"target {target.id} has duplicate grant: {', '.join(duplicate_grants)}"
            )
        outside_pool = sorted(set(target.grants) - pool)
        if outside_pool:
            raise ResolutionError(
                f"target {target.id} grants skills outside pool: {', '.join(outside_pool)}"
            )
        absent = sorted(set(target.grants) - set(locked))
        if absent:
            raise ResolutionError(
                f"target {target.id} grants artifacts absent from lock: {', '.join(absent)}"
            )

        runtime_names: dict[str, str] = {}
        links: list[DesiredLink] = []
        normalized_root = Path(os.path.abspath(target.root))
        for artifact_id in sorted(target.grants):
            skill = locked[artifact_id]
            previous_artifact = runtime_names.get(skill.runtime_name)
            if previous_artifact is not None:
                raise ResolutionError(
                    f"target {target.id} has duplicate runtime name {skill.runtime_name!r}: "
                    f"{previous_artifact}, {artifact_id}"
                )
            runtime_names[skill.runtime_name] = artifact_id

            target_path = _target_path(normalized_root, artifact_id)
            previous_placement = occupied_paths.get(target_path)
            if previous_placement is not None:
                previous_target, previous_id = previous_placement
                raise ResolutionError(
                    f"target path collision at {target_path}: "
                    f"{previous_target}/{previous_id} and {target.id}/{artifact_id}"
                )
            occupied_paths[target_path] = (target.id, artifact_id)
            links.append(
                DesiredLink(
                    artifact_id=artifact_id,
                    runtime_name=skill.runtime_name,
                    source_path=skill.path,
                    target_path=target_path,
                    content_sha256=skill.sha256,
                )
            )
        desired_targets.append(DesiredTarget(target.id, normalized_root, tuple(links)))

    return DesiredState(tuple(desired_targets))
