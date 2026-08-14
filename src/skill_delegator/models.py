"""Immutable configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSpec:
    """A declared source of skills."""

    id: str
    type: str
    location: Path
    skill_root: Path


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
