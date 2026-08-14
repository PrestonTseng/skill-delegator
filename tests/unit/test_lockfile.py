from __future__ import annotations

import errno
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest
import yaml

from skill_delegator import source_store
from skill_delegator.errors import SourceError
from skill_delegator.inventory import hash_tree
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


@pytest.mark.parametrize(
    "track",
    ("feature", "refs/heads/feature", "refs/remotes/origin/feature", "refs/tags/v1"),
)
def test_resolves_local_clone_refs_deterministically(tmp_path: Path, track: str) -> None:
    repo = tmp_path / "repo"
    first, _ = init_git_source(repo)
    git(repo, "branch", "feature", first)
    git(repo, "tag", "v1", first)
    source = SourceSpec("upstream", "git", str(repo), PurePosixPath("skills"), track)

    resolved = resolve_sources(config_for(source), tmp_path / "cache")

    assert resolved[0].revision == first


@pytest.mark.parametrize("broken", (False, True), ids=("escape", "broken"))
def test_rejects_symlink_anywhere_in_source_before_cache_publication(
    tmp_path: Path, broken: bool
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    outside = tmp_path / "outside"
    if not broken:
        outside.write_text("external", encoding="utf-8")
    (source_root / "unrelated-link").symlink_to(outside)
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)
    cache = tmp_path / "cache"

    with pytest.raises(SourceError, match="broken symlink|symlink escape"):
        resolve_sources(config_for(source), cache)

    assert not cache.exists()


def test_rejects_cache_key_symlink_even_when_external_tree_hash_matches(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    revision = hash_tree(source_root)
    external = tmp_path / "external"
    shutil.copytree(source_root, external, symlinks=True)
    destination = tmp_path / "cache" / "local" / revision
    destination.parent.mkdir(parents=True)
    destination.symlink_to(external, target_is_directory=True)
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)

    with pytest.raises(SourceError, match="cache.*symlink|cache.*confined"):
        resolve_sources(config_for(source), tmp_path / "cache")

    assert destination.is_symlink()
    assert (external / "skills" / "one" / "SKILL.md").is_file()


def test_rejects_source_absolute_symlink_that_would_escape_copied_snapshot(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    internal = source_root / "internal"
    internal.write_text("content", encoding="utf-8")
    (source_root / "absolute-link").symlink_to(internal.resolve())
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)
    cache = tmp_path / "cache"

    with pytest.raises(SourceError, match="symlink escape from copied snapshot root"):
        resolve_sources(config_for(source), cache)

    assert not cache.exists()


def test_rejects_git_symlink_before_untrusted_checkout_enters_cache(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    init_git_source(repo)
    outside = tmp_path / "outside"
    outside.write_text("external", encoding="utf-8")
    (repo / "unrelated-link").symlink_to(outside)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "unsafe link")
    revision = git(repo, "rev-parse", "HEAD")
    source = SourceSpec("upstream", "git", str(repo), PurePosixPath("skills"), revision)
    cache = tmp_path / "cache"

    with pytest.raises(SourceError, match="symlink escape from source root"):
        resolve_sources(config_for(source), cache)

    assert not cache.exists()


@pytest.mark.parametrize("symlink_level", ("root", "source"))
def test_rejects_symlinked_cache_root_state(tmp_path: Path, symlink_level: str) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    external = tmp_path / "external-cache"
    external.mkdir()
    cache = tmp_path / "cache"
    if symlink_level == "root":
        cache.symlink_to(external, target_is_directory=True)
    else:
        cache.mkdir()
        (cache / "local").symlink_to(external, target_is_directory=True)
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)

    with pytest.raises(SourceError, match="cache.*symlink|cache.*confined"):
        resolve_sources(config_for(source), cache)

    assert tuple(external.iterdir()) == ()


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


def test_build_lock_requires_canonical_id_to_equal_relative_path(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/actual")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)
    resolved = resolve_sources(config_for(source), tmp_path / "cache")[0]
    mismatched_skill = replace(resolved.skills[0], canonical_id="local/different")
    mismatched = replace(resolved, skills=(mismatched_skill,))

    with pytest.raises(SourceError, match="canonical.*relative path|incorrect canonical"):
        build_lock(config_for(source), (mismatched,))


@pytest.mark.parametrize("race_errno", (errno.ENOTEMPTY, errno.EEXIST))
def test_cache_race_accepts_concurrent_matching_real_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, race_errno: int
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)
    original_rename = Path.rename

    def compete(staging: Path, destination: Path) -> Path:
        if staging.name.startswith(".snapshot-"):
            shutil.copytree(source_root, destination, symlinks=True)
            raise OSError(race_errno, "competing directory")
        return original_rename(staging, destination)

    monkeypatch.setattr(source_store.Path, "rename", compete)

    resolved = resolve_sources(config_for(source), tmp_path / "cache")

    assert hash_tree(resolved[0].root) == resolved[0].revision
    assert not tuple((tmp_path / "cache" / "local").glob(".snapshot-*"))


def test_cache_race_wraps_concurrent_corrupt_directory_and_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)

    def compete(staging: Path, destination: Path) -> Path:
        destination.mkdir()
        (destination / "corrupt").write_text("wrong", encoding="utf-8")
        raise OSError(errno.ENOTEMPTY, "competing directory")

    monkeypatch.setattr(source_store.Path, "rename", compete)

    with pytest.raises(SourceError, match="cache race produced corrupt entry"):
        resolve_sources(config_for(source), tmp_path / "cache")

    assert not tuple((tmp_path / "cache" / "local").glob(".snapshot-*"))


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
