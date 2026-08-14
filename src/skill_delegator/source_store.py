"""Resolve declared sources into immutable content-addressed snapshots."""

from __future__ import annotations

import errno
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from skill_delegator.errors import SourceError
from skill_delegator.inventory import (
    discover_skills,
    hash_tree,
    validate_snapshot_tree,
    validate_source_tree,
)
from skill_delegator.models import AuthorityConfig, ResolvedSkill, ResolvedSource, SourceSpec

_GIT_TIMEOUT_SECONDS = 30
_MAX_GIT_ERROR_CHARS = 2000
_MAX_OS_ERROR_CHARS = 500


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


def _ensure_real_cache_directory(path: Path, *, description: str) -> Path:
    """Create and validate one managed cache directory without following a symlink."""

    try:
        path.mkdir(parents=True, exist_ok=True)
        metadata = path.lstat()
    except OSError as error:
        detail = str(error)[:_MAX_OS_ERROR_CHARS]
        raise SourceError(f"cannot prepare {description} {path}: {detail}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise SourceError(f"{description} must not be a symlink: {path}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise SourceError(f"{description} is not a directory: {path}")
    return path


def _existing_cache_entry(destination: Path, cache_root: Path, expected_hash: str) -> bool:
    """Validate a cache key using lstat and resolved confinement, or report it absent."""

    try:
        metadata = destination.lstat()
    except FileNotFoundError:
        return False
    except OSError as error:
        detail = str(error)[:_MAX_OS_ERROR_CHARS]
        raise SourceError(
            f"cannot inspect content-addressed cache entry {destination}: {detail}"
        ) from error
    if stat.S_ISLNK(metadata.st_mode):
        raise SourceError(f"content-addressed cache entry must not be a symlink: {destination}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise SourceError(f"content-addressed cache entry is corrupt: {destination}")
    try:
        resolved_destination = destination.resolve(strict=True)
        resolved_cache_root = cache_root.resolve(strict=True)
    except OSError as error:
        detail = str(error)[:_MAX_OS_ERROR_CHARS]
        raise SourceError(
            f"cannot resolve content-addressed cache entry {destination}: {detail}"
        ) from error
    if not resolved_destination.is_relative_to(resolved_cache_root):
        raise SourceError(f"content-addressed cache entry is not confined: {destination}")
    validate_source_tree(destination)
    if hash_tree(destination) != expected_hash:
        raise SourceError(f"content-addressed cache entry is corrupt: {destination}")
    return True


def _source_cache_root(cache_root: Path, source_id: str) -> tuple[Path, Path]:
    lexical_root = Path(os.path.abspath(cache_root))
    if Path(source_id).parts != (source_id,) or source_id in {"", ".", ".."}:
        raise SourceError(f"source id cannot form a confined cache path: {source_id!r}")
    _ensure_real_cache_directory(lexical_root, description="content-addressed cache root")
    source_cache = lexical_root / source_id
    _ensure_real_cache_directory(source_cache, description="source cache directory")
    if not source_cache.resolve(strict=True).is_relative_to(lexical_root.resolve(strict=True)):
        raise SourceError(f"source cache directory is not confined: {source_cache}")
    return lexical_root, source_cache


def _cache_snapshot(
    source_root: Path, destination: Path, expected_hash: str, cache_root: Path
) -> Path:
    if _existing_cache_entry(destination, cache_root, expected_hash):
        return destination
    staging = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=destination.parent))
    try:
        shutil.rmtree(staging)
        shutil.copytree(source_root, staging, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        validate_source_tree(staging)
        if hash_tree(staging) != expected_hash:
            raise SourceError("source changed while its snapshot was being created")
        try:
            staging.rename(destination)
        except OSError as error:
            if error.errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                detail = str(error)[:_MAX_OS_ERROR_CHARS]
                raise SourceError(
                    f"cannot publish content-addressed cache entry: {detail}"
                ) from error
            try:
                valid_race_entry = _existing_cache_entry(destination, cache_root, expected_hash)
            except SourceError as validation_error:
                raise SourceError(
                    f"content-addressed cache race produced corrupt entry: {destination}: "
                    f"{validation_error}"
                ) from error
            if not valid_race_entry:
                raise SourceError(
                    f"content-addressed cache race did not produce an entry: {destination}"
                ) from error
        if not _existing_cache_entry(destination, cache_root, expected_hash):
            raise SourceError(f"published content-addressed cache entry disappeared: {destination}")
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
    # Validate the full source before creating any cache state or publishing links.
    validate_snapshot_tree(source.location)
    discover_skills(source.location, source.skill_root)
    revision = hash_tree(source.location)
    lexical_cache_root, source_cache = _source_cache_root(cache_root, source.id)
    destination = source_cache / revision
    snapshot = _cache_snapshot(source.location, destination, revision, lexical_cache_root)
    return ResolvedSource(
        source_id=source.id,
        source_type=source.type,
        location=str(source.location),
        revision=revision,
        root=snapshot,
        skills=_resolved_skills(source, snapshot),
    )


def _tracked_commit_ref(track: str) -> str:
    if track.startswith("refs/heads/"):
        return f"refs/remotes/origin/{track.removeprefix('refs/heads/')}"
    if track.startswith(("refs/remotes/", "refs/tags/")):
        return track
    if track.startswith("origin/"):
        return f"refs/remotes/{track}"
    if len(track) == 40 and all(character in "0123456789abcdefABCDEF" for character in track):
        return track
    return f"refs/remotes/origin/{track}"


def _resolve_git(source: SourceSpec, cache_root: Path) -> ResolvedSource:
    if not isinstance(source.location, str) or not source.track:
        raise SourceError(f"git source {source.id} requires string location and tracked ref")
    temporary = Path(tempfile.mkdtemp(prefix=".git-resolve-"))
    checkout = temporary / "checkout"
    try:
        _run_git(["clone", "--quiet", "--no-checkout", "--", source.location, str(checkout)])
        revision = _run_git(
            [
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{_tracked_commit_ref(source.track)}^{{commit}}",
            ],
            cwd=checkout,
        )
        if len(revision) != 40 or any(
            character not in "0123456789abcdef" for character in revision
        ):
            raise SourceError(f"git source {source.id} did not resolve to a SHA-1 commit")
        _run_git(["checkout", "--quiet", "--detach", revision], cwd=checkout)
        shutil.rmtree(checkout / ".git")
        # Validate the entire checkout before publishing any source-controlled links.
        validate_snapshot_tree(checkout)
        discover_skills(checkout, source.skill_root)
        tree_hash = hash_tree(checkout)
        lexical_cache_root, source_cache = _source_cache_root(cache_root, source.id)
        destination = source_cache / revision
        snapshot = _cache_snapshot(checkout, destination, tree_hash, lexical_cache_root)
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
