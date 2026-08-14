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
    cache_root: Path | None = None


@dataclass(frozen=True)
class SourceUpdate:
    """Bounded evidence comparing a mutable source selector to an exact lock."""

    source_id: str
    source_type: str
    old_revision: str
    new_revision: str | None
    relation: str


@dataclass(frozen=True)
class ArtifactUpdate:
    """Hash-only review evidence for one authority-relevant artifact."""

    canonical_id: str
    old_sha256: str | None
    new_sha256: str | None
    status: str


@dataclass(frozen=True)
class LockUpdateProposal:
    """Validated immutable candidate lock and its bounded review evidence."""

    source: SourceUpdate
    candidate_lock: SkillLock
    artifacts: tuple[ArtifactUpdate, ...]
    new_ungranted: tuple[str, ...]
    removed_ungranted: tuple[str, ...]


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
    tree_hash: str
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
class DesiredSource:
    """Exact complete cached snapshot required by desired state."""

    source_id: str
    root: Path
    tree_hash: str


@dataclass(frozen=True)
class DesiredState:
    """Pure resolved desired state for an authority."""

    targets: tuple[DesiredTarget, ...]
    sources: tuple[DesiredSource, ...] = ()


@dataclass(frozen=True)
class ManagedEntry:
    """One manager-owned link validated against its metadata record."""

    artifact_id: str
    relative_path: PurePosixPath
    source_path: Path
    content_sha256: str
    raw_link_target: str | None = None


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
    root_exists: bool = True


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
class PlanTarget:
    """Apply authority bound into an immutable reviewed plan."""

    id: str
    root: Path
    cache_root: Path
    current_fingerprint: str
    desired_entries: tuple[ManagedEntry, ...]


@dataclass(frozen=True)
class ReconciliationPlan:
    """Immutable plan; blockers prohibit every mutating operation."""

    operations: tuple[PlanOperation, ...]
    blocked: tuple[str, ...]
    targets: tuple[PlanTarget, ...] = ()

    @property
    def has_changes(self) -> bool:
        return any(
            operation.action in {"CREATE", "REPLACE", "REMOVE"} for operation in self.operations
        )


@dataclass(frozen=True)
class VerificationReason:
    """One bounded, deterministic verification finding."""

    code: str
    category: str
    target_id: str | None
    artifact_id: str | None
    detail: str


@dataclass(frozen=True)
class TargetFingerprint:
    """Content identity of one freshly observed target."""

    target_id: str
    sha256: str


@dataclass(frozen=True)
class ConfigFileHash:
    """Byte identity of one desired-state input file."""

    name: str
    sha256: str


@dataclass(frozen=True)
class LockedSourceIdentity:
    """Exact immutable identity recorded for a locked source."""

    source_id: str
    source_type: str
    revision_kind: str
    revision: str
    tree_identity: str | None


@dataclass(frozen=True)
class SourceTreeEvidence:
    """Fresh whole-snapshot identity observed independently of target links."""

    source_id: str
    sha256: str


@dataclass(frozen=True)
class OperationSummary:
    """Deterministic aggregate of desired and freshly verified state."""

    desired_targets: int
    desired_links: int
    verified_links: int
    drift_count: int
    invalid_count: int


@dataclass(frozen=True)
class VerificationResult:
    """Immutable verification evidence, suitable for deterministic receipts."""

    result: str
    reasons: tuple[VerificationReason, ...]
    target_fingerprints: tuple[TargetFingerprint, ...]
    operation_summary: OperationSummary
    authority_id: str = "unbound"
    repository_commit: str | None = None
    repository_commit_available: bool = False
    config_hashes: tuple[ConfigFileHash, ...] = ()
    locked_sources: tuple[LockedSourceIdentity, ...] = ()
    source_tree_evidence: tuple[SourceTreeEvidence, ...] = ()

    @property
    def converged(self) -> bool:
        return self.result == "converged"
