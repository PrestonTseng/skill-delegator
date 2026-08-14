"""Resolve declared sources into immutable content-addressed snapshots."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from skill_delegator.errors import SourceError
from skill_delegator.inventory import discover_skills, hash_tree
from skill_delegator.models import AuthorityConfig, ResolvedSkill, ResolvedSource, SourceSpec

_GIT_TIMEOUT_SECONDS = 30
_MAX_GIT_ERROR_CHARS = 2000


def _run_git(args: list[str], *, cwd: Path | None = None) -> str:
    command = ["git", *args]
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SourceError(f"git command failed: {command[1]}: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:_MAX_GIT_ERROR_CHARS]
        raise SourceError(f"git command failed ({command[1]}): {detail}")
    return result.stdout.strip()


def _cache_snapshot(source_root: Path, destination: Path, expected_hash: str) -> Path:
    if destination.exists():
        if not destination.is_dir() or hash_tree(destination) != expected_hash:
            raise SourceError(f"content-addressed cache entry is corrupt: {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=destination.parent))
    try:
        shutil.rmtree(staging)
        shutil.copytree(source_root, staging, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        if hash_tree(staging) != expected_hash:
            raise SourceError("source changed while its snapshot was being created")
        try:
            staging.rename(destination)
        except FileExistsError:
            if hash_tree(destination) != expected_hash:
                raise SourceError(
                    f"content-addressed cache race produced corrupt entry: {destination}"
                )
        return destination
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _resolved_skills(source: SourceSpec, root: Path) -> tuple[ResolvedSkill, ...]:
    artifacts = discover_skills(root, source.skill_root)
    skills: list[ResolvedSkill] = []
    seen: set[str] = set()
    for artifact in artifacts:
        canonical_id = f"{source.id}/{artifact.relative_path.as_posix()}"
        if canonical_id in seen:
            raise SourceError(f"duplicate canonical artifact id: {canonical_id}")
        seen.add(canonical_id)
        skills.append(
            ResolvedSkill(
                canonical_id=canonical_id,
                relative_path=artifact.relative_path,
                runtime_name=artifact.runtime_name,
                description=artifact.description,
                sha256=artifact.sha256,
            )
        )
    return tuple(skills)


def _resolve_filesystem(source: SourceSpec, cache_root: Path) -> ResolvedSource:
    if not isinstance(source.location, Path):
        raise SourceError(f"filesystem source {source.id} location must be a Path")
    # Discovery first ensures escaping/broken symlinks fail before cache publication.
    discover_skills(source.location, source.skill_root)
    revision = hash_tree(source.location)
    destination = cache_root / source.id / revision
    snapshot = _cache_snapshot(source.location, destination, revision)
    return ResolvedSource(
        source_id=source.id,
        source_type=source.type,
        location=str(source.location),
        revision=revision,
        root=snapshot,
        skills=_resolved_skills(source, snapshot),
    )


def _resolve_git(source: SourceSpec, cache_root: Path) -> ResolvedSource:
    if not isinstance(source.location, str) or not source.track:
        raise SourceError(f"git source {source.id} requires string location and tracked ref")
    source_cache = cache_root / source.id
    source_cache.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".git-resolve-", dir=source_cache))
    checkout = temporary / "checkout"
    try:
        _run_git(["clone", "--quiet", "--no-checkout", "--", source.location, str(checkout)])
        revision = _run_git(
            ["rev-parse", "--verify", "--end-of-options", f"{source.track}^{{commit}}"],
            cwd=checkout,
        )
        if len(revision) != 40 or any(
            character not in "0123456789abcdef" for character in revision
        ):
            raise SourceError(f"git source {source.id} did not resolve to a SHA-1 commit")
        destination = source_cache / revision
        _run_git(["checkout", "--quiet", "--detach", revision], cwd=checkout)
        shutil.rmtree(checkout / ".git")
        # Validate confinement before publishing any source-controlled links.
        discover_skills(checkout, source.skill_root)
        tree_hash = hash_tree(checkout)
        snapshot = _cache_snapshot(checkout, destination, tree_hash)
        skills = _resolved_skills(source, snapshot)
        return ResolvedSource(
            source_id=source.id,
            source_type=source.type,
            location=source.location,
            revision=revision,
            root=snapshot,
            skills=skills,
        )
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def resolve_sources(config: AuthorityConfig, cache_root: Path) -> tuple[ResolvedSource, ...]:
    """Resolve all sources, sorted by ID, into exact cached snapshots."""

    resolved: list[ResolvedSource] = []
    for source in sorted(config.sources, key=lambda item: item.id):
        if source.type == "filesystem":
            resolved.append(_resolve_filesystem(source, cache_root))
        elif source.type == "git":
            resolved.append(_resolve_git(source, cache_root))
        else:
            raise SourceError(f"unsupported source type: {source.type}")
    return tuple(resolved)
