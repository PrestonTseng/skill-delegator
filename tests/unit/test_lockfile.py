from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest
import yaml

from skill_delegator.errors import SourceError
from skill_delegator.lockfile import build_lock, serialize_lock, write_lock_atomic
from skill_delegator.models import AuthorityConfig, PoolSpec, SourceSpec
from skill_delegator.source_store import resolve_sources


def write_skill(root: Path, relative: str, name: str = "runtime") -> None:
    directory = root / relative
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test description\n---\nbody\n",
        encoding="utf-8",
    )


def config_for(*sources: SourceSpec, pool: tuple[str, ...] = ()) -> AuthorityConfig:
    return AuthorityConfig(
        authority_id="test",
        fail_closed=True,
        fixture_policy="none",
        sources=sources,
        pool=tuple(PoolSpec(item) for item in pool),
        targets=(),
    )


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def init_git_source(path: Path) -> tuple[str, str]:
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "user.name", "Test")
    write_skill(path, "skills/one", "one")
    git(path, "add", ".")
    git(path, "commit", "-qm", "one")
    first = git(path, "rev-parse", "HEAD")
    (path / "skills" / "one" / "extra").write_text("second", encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-qm", "two")
    return first, git(path, "rev-parse", "HEAD")


def test_config_preserves_git_location_as_string_and_resolves_filesystem_location(
    tmp_path: Path,
) -> None:
    filesystem = SourceSpec("fs", "filesystem", tmp_path.resolve(), PurePosixPath("."), None)
    git_source = SourceSpec(
        "git", "git", "ssh://example.invalid/repository.git", PurePosixPath("skills"), "main"
    )

    assert isinstance(filesystem.location, Path)
    assert isinstance(git_source.location, str)


def test_resolves_exact_git_commit_into_content_addressed_cache(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    first, second = init_git_source(repo)
    source = SourceSpec("upstream", "git", str(repo), PurePosixPath("skills"), first)

    resolved = resolve_sources(config_for(source), tmp_path / "cache")

    assert resolved[0].revision == first
    assert resolved[0].revision != second
    assert resolved[0].root == tmp_path / "cache" / "upstream" / first
    assert resolved[0].root.is_dir()
    assert resolved[0].skills[0].canonical_id == "upstream/one"
    locked = build_lock(config_for(source), resolved)
    assert locked.sources[0].resolved_commit == first
    assert locked.sources[0].tree_hash is None
    document = yaml.safe_load(serialize_lock(locked))
    assert document["sources"][0]["resolved_commit"] == first
    assert "tree_hash" not in document["sources"][0]


def test_filesystem_tree_hash_is_revision_and_cache_key(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)

    first = resolve_sources(config_for(source), tmp_path / "cache")[0]
    (source_root / "skills" / "one" / "extra").write_text("changed", encoding="utf-8")
    second = resolve_sources(config_for(source), tmp_path / "cache")[0]

    assert len(first.revision) == 64
    assert first.revision != second.revision
    assert first.root.name == first.revision
    assert second.root.name == second.revision
    locked = build_lock(config_for(source), (second,))
    assert locked.sources[0].tree_hash == second.revision
    assert locked.sources[0].resolved_commit is None


def test_build_lock_rejects_duplicate_canonical_artifact_ids(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    resolved = resolve_sources(config_for(source), tmp_path / "cache")[0]
    duplicated = replace(resolved, skills=(resolved.skills[0], resolved.skills[0]))

    with pytest.raises(SourceError, match="duplicate canonical artifact"):
        build_lock(config_for(source), (duplicated,))


def test_build_lock_requires_every_pool_reference(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    config = config_for(source, pool=("local/missing",))
    resolved = resolve_sources(config, tmp_path / "cache")

    with pytest.raises(SourceError, match="missing locked skill.*local/missing"):
        build_lock(config, resolved)


def test_lock_serialization_and_atomic_write_are_byte_stable(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "z", "z")
    write_skill(source_root, "a", "a")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    config = config_for(source)
    lock = build_lock(config, resolve_sources(config, tmp_path / "cache"))

    first = serialize_lock(lock)
    path = tmp_path / "skill-lock.yaml"
    write_lock_atomic(path, lock)
    first_stat = path.stat()
    write_lock_atomic(path, lock)

    assert path.read_bytes() == first
    assert serialize_lock(lock) == first
    assert path.stat().st_ino != 0
    assert first_stat.st_mode == path.stat().st_mode
