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
from skill_delegator.safe_paths import AnchoredDirectory, open_anchored_directory

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


def _ensure_real_cache_directory(path: Path, *, description: str) -> AnchoredDirectory:
    """Create/traverse a cache path descriptor-relative without following links."""

    return open_anchored_directory(path, description=description.replace(" ", "-"))


def _existing_cache_entry(cache: AnchoredDirectory, name: str, expected_hash: str) -> bool:
    """Validate one cache key through its retained source-cache descriptor."""

    try:
        metadata = os.stat(name, dir_fd=cache.fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        detail = str(error)[:_MAX_OS_ERROR_CHARS]
        raise SourceError(f"cannot inspect content-addressed cache entry: {detail}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise SourceError("content-addressed cache entry must not be a symlink")
    if not stat.S_ISDIR(metadata.st_mode):
        raise SourceError("content-addressed cache entry is corrupt")
    destination = cache.descriptor_path / name
    validate_source_tree(destination)
    if hash_tree(destination) != expected_hash:
        raise SourceError("content-addressed cache entry is corrupt")
    cache.verify(description="content-addressed-cache")
    return True


def _source_cache_root(cache_root: Path, source_id: str) -> AnchoredDirectory:
    lexical_root = Path(os.path.abspath(cache_root))
    if Path(source_id).parts != (source_id,) or source_id in {"", ".", ".."}:
        raise SourceError(f"source id cannot form a confined cache path: {source_id!r}")
    cache = _ensure_real_cache_directory(lexical_root, description="content-addressed cache root")
    try:
        cache.open_child(source_id, description="cache-source-directory")
        cache.verify(description="content-addressed-cache")
    except Exception:
        cache.close()
        raise
    return cache


def _cache_snapshot(
    source_root: Path, cache: AnchoredDirectory, cache_key: str, expected_hash: str
) -> Path:
    if _existing_cache_entry(cache, cache_key, expected_hash):
        return cache.descriptor_path / cache_key
    cache.verify(description="content-addressed-cache")
    staging = Path(tempfile.mkdtemp(prefix=".snapshot-", dir=cache.descriptor_path))
    destination = cache.descriptor_path / cache_key
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
                valid_race_entry = _existing_cache_entry(cache, cache_key, expected_hash)
            except SourceError:
                raise SourceError(
                    "content-addressed cache race produced corrupt entry: validation-failed"
                ) from error
            if not valid_race_entry:
                raise SourceError(
                    "content-addressed cache race did not produce an entry"
                ) from error
        if not _existing_cache_entry(cache, cache_key, expected_hash):
            raise SourceError("published content-addressed cache entry disappeared")
        cache.verify(description="content-addressed-cache")
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
    cache = _source_cache_root(cache_root, source.id)
    try:
        snapshot = _cache_snapshot(source.location, cache, revision, revision)
        skills = _resolved_skills(source, snapshot)
        cache.verify(description="content-addressed-cache")
    finally:
        cache.close()
    return ResolvedSource(
        source_id=source.id,
        source_type=source.type,
        location=str(source.location),
        revision=revision,
        root=Path(os.path.abspath(cache_root)) / source.id / revision,
        skills=skills,
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
        cache = _source_cache_root(cache_root, source.id)
        try:
            snapshot = _cache_snapshot(checkout, cache, revision, tree_hash)
            skills = _resolved_skills(source, snapshot)
            cache.verify(description="content-addressed-cache")
        finally:
            cache.close()
        return ResolvedSource(
            source_id=source.id,
            source_type=source.type,
            location=source.location,
            revision=revision,
            root=Path(os.path.abspath(cache_root)) / source.id / revision,
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
