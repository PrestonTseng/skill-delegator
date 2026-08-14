"""Immutable configuration, inventory, and lock models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class SourceSpec:
    """A declared source of skills.

    Filesystem locations are absolute :class:`Path` objects. Git locations remain
    repository strings and are intentionally not interpreted as local paths.
    """

    id: str
    type: str
    location: str | Path
    skill_root: PurePosixPath
    track: str | None = None


@dataclass(frozen=True)
class PoolSpec:
    """One canonical skill admitted to the authority's pool."""

    canonical_id: str


@dataclass(frozen=True)
class TargetSpec:
    """A target root and its granted canonical skills."""

    id: str
    root: Path
    grants: tuple[str, ...]


@dataclass(frozen=True)
class AuthorityConfig:
    """A fully validated authority configuration."""

    authority_id: str
    fail_closed: bool
    fixture_policy: str
    sources: tuple[SourceSpec, ...]
    pool: tuple[PoolSpec, ...]
    targets: tuple[TargetSpec, ...]


@dataclass(frozen=True)
class SkillArtifact:
    """One discovered skill directory with content identity."""

    relative_path: PurePosixPath
    runtime_name: str
    description: str
    sha256: str


@dataclass(frozen=True)
class ResolvedSkill:
    """A source-qualified skill artifact."""

    canonical_id: str
    relative_path: PurePosixPath
    runtime_name: str
    description: str
    sha256: str


@dataclass(frozen=True)
class ResolvedSource:
    """An immutable source snapshot in the content-addressed cache."""

    source_id: str
    source_type: str
    location: str
    revision: str
    root: Path
    skills: tuple[ResolvedSkill, ...]


@dataclass(frozen=True)
class LockedSkill:
    """Exact lock record for one canonical skill."""

    canonical_id: str
    runtime_name: str
    path: PurePosixPath
    sha256: str


@dataclass(frozen=True)
class LockedSource:
    """Exact lock record for one source snapshot."""

    source_id: str
    source_type: str
    resolved_commit: str | None
    tree_hash: str | None
    skills: tuple[LockedSkill, ...]


@dataclass(frozen=True)
class SkillLock:
    """Complete deterministic source lock."""

    schema_version: int
    sources: tuple[LockedSource, ...]


@dataclass(frozen=True)
class DesiredLink:
    """One exact artifact placement in a target's desired state."""

    artifact_id: str
    runtime_name: str
    source_path: PurePosixPath
    target_path: Path
    content_sha256: str
    expected_source_path: Path | None = None


@dataclass(frozen=True)
class DesiredTarget:
    """Deterministically ordered desired links for one target."""

    id: str
    root: Path
    links: tuple[DesiredLink, ...]


@dataclass(frozen=True)
class DesiredState:
    """Pure resolved desired state for an authority."""

    targets: tuple[DesiredTarget, ...]


@dataclass(frozen=True)
class ManagedEntry:
    """One manager-owned link validated against its metadata record."""

    artifact_id: str
    relative_path: PurePosixPath
    source_path: Path
    content_sha256: str


@dataclass(frozen=True)
class UnmanagedEntry:
    """One target entry that the manager must preserve."""

    relative_path: PurePosixPath
    kind: str
    link_target: str | None


@dataclass(frozen=True)
class CurrentTargetState:
    """Read-only, deterministically ordered state of one target."""

    id: str
    root: Path
    managed: tuple[ManagedEntry, ...]
    unmanaged: tuple[UnmanagedEntry, ...]
    cache_root: Path | None = None


@dataclass(frozen=True)
class CurrentState:
    """Read-only current state for all desired targets."""

    targets: tuple[CurrentTargetState, ...]
    expected_cache_root: Path | None = None


@dataclass(frozen=True)
class PlanOperation:
    """One deterministic reconciliation or preservation decision."""

    action: str
    target_id: str
    artifact_id: str | None
    relative_path: PurePosixPath
    current_source_path: Path | None = None
    desired_source_path: Path | None = None
    entry_kind: str | None = None


@dataclass(frozen=True)
class ReconciliationPlan:
    """Immutable plan; blockers prohibit every mutating operation."""

    operations: tuple[PlanOperation, ...]
    blocked: tuple[str, ...]

    @property
    def has_changes(self) -> bool:
        return any(
            operation.action in {"CREATE", "REPLACE", "REMOVE"} for operation in self.operations
        )
