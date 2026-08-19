from __future__ import annotations

import errno
import os
import shutil
import stat
import subprocess
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest
import yaml

from skill_delegator import lockfile, source_store
from skill_delegator.errors import SourceError
from skill_delegator.inventory import hash_tree
from skill_delegator.lockfile import build_lock, serialize_lock, write_lock_atomic
from skill_delegator.models import AuthorityConfig, PoolSpec, SkillLock, SourceSpec
from skill_delegator.safe_paths import AnchoredDirectory
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
    assert locked.sources[0].tree_hash == hash_tree(resolved[0].root)
    document = yaml.safe_load(serialize_lock(locked))
    assert document["sources"][0]["resolved_commit"] == first
    assert document["sources"][0]["tree_hash"] == locked.sources[0].tree_hash


@pytest.mark.parametrize("swap_level", ("source", "ancestor"))
def test_filesystem_source_swap_uses_retained_inode_and_never_caches_outside_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_level: str
) -> None:
    parent = tmp_path / "parent"
    source_root = parent / "source"
    write_skill(source_root, "skills/original", "original")
    outside = tmp_path / "outside-parent" / "source"
    write_skill(outside, "skills/raced", "raced")
    original_bytes = (source_root / "skills" / "original" / "SKILL.md").read_bytes()
    outside_bytes = (outside / "skills" / "raced" / "SKILL.md").read_bytes()
    assert original_bytes != outside_bytes
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)
    cache = tmp_path / "cache"
    real_validate = source_store.validate_tree_at
    fired = False

    def swap_after_open(root_fd: int, *, snapshot: bool) -> None:
        nonlocal fired
        if not fired:
            fired = True
            if swap_level == "source":
                source_root.rename(parent / "source-original")
                source_root.symlink_to(outside, target_is_directory=True)
            else:
                parent.rename(tmp_path / "parent-original")
                parent.symlink_to(outside.parent, target_is_directory=True)
        real_validate(root_fd, snapshot=snapshot)

    monkeypatch.setattr(source_store, "validate_tree_at", swap_after_open)

    with pytest.raises(SourceError, match="filesystem-source-identity-changed"):
        resolve_sources(config_for(source), cache)

    assert fired
    assert source_root.resolve() == outside
    assert (
        (outside / "skills" / "raced" / "SKILL.md")
        .read_text(encoding="utf-8")
        .startswith("---\nname: raced\n")
    )
    if cache.exists():
        assert not any(path.name == "raced" for path in cache.rglob("*"))
        assert not any(
            path.is_file() and path.read_bytes() == outside_bytes for path in cache.rglob("*")
        )
        assert not any(cache.rglob("*"))


def test_cache_path_swap_never_writes_outside_retained_inode_and_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    cache_root = tmp_path / "cache"
    lexical_source_cache = cache_root / "local"
    retained_cache = tmp_path / "retained-cache"
    external_cache = tmp_path / "external-cache"
    external_cache.mkdir()
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    real_copy = source_store.copy_tree_into_at
    fired = False

    def swap_then_copy(source_fd: int, destination_fd: int) -> None:
        nonlocal fired
        if not fired:
            fired = True
            lexical_source_cache.rename(retained_cache)
            lexical_source_cache.symlink_to(external_cache, target_is_directory=True)
        real_copy(source_fd, destination_fd)

    monkeypatch.setattr(source_store, "copy_tree_into_at", swap_then_copy)

    with pytest.raises(SourceError, match="content-addressed-cache"):
        resolve_sources(config_for(source), cache_root)

    assert fired
    assert tuple(external_cache.iterdir()) == ()
    assert tuple(retained_cache.iterdir()) == ()


def test_existing_cache_entry_replacement_during_hash_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    cache_root = tmp_path / "cache"
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    first = resolve_sources(config_for(source), cache_root)[0]
    lexical_entry = first.root
    retained_entry = tmp_path / "retained-entry"
    real_hash = source_store.hash_tree_at
    calls = 0

    def swap_after_hash(root_fd: int) -> str:
        nonlocal calls
        calls += 1
        digest = real_hash(root_fd)
        if calls == 2:
            lexical_entry.rename(retained_entry)
            lexical_entry.mkdir()
            (lexical_entry / "CORRUPT").write_text("hostile", encoding="utf-8")
        return digest

    monkeypatch.setattr(source_store, "hash_tree_at", swap_after_hash)

    with pytest.raises(SourceError, match="content-addressed-cache-entry-identity-changed"):
        resolve_sources(config_for(source), cache_root)

    assert calls >= 2
    assert tuple(path.name for path in lexical_entry.iterdir()) == ("CORRUPT",)
    assert (retained_entry / "one" / "SKILL.md").is_file()


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


@pytest.mark.parametrize("bad_component", ("var", "cache", "sources"))
@pytest.mark.parametrize("kind", ("symlink", "file"))
def test_rejects_every_untrusted_cache_ancestor_without_touching_external_state(
    tmp_path: Path, bad_component: str, kind: str
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    project = tmp_path / "project"
    cache = project / "var" / "cache" / "sources"
    component = {
        "var": project / "var",
        "cache": project / "var" / "cache",
        "sources": project / "var" / "cache" / "sources",
    }[bad_component]
    component.parent.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel"
    sentinel.write_bytes(b"unchanged")
    if kind == "symlink":
        component.symlink_to(external, target_is_directory=True)
    else:
        component.write_bytes(b"not-a-directory")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)

    with pytest.raises(SourceError, match="cache"):
        resolve_sources(config_for(source), cache)

    assert sentinel.read_bytes() == b"unchanged"
    assert tuple(external.iterdir()) == (sentinel,)


@pytest.mark.parametrize("replaced", ("var", "cache", "source-cache"))
def test_candidate_cache_writes_fail_closed_when_retained_ancestor_is_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replaced: str
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    project = tmp_path / "project"
    cache = project / "var" / "cache" / "sources"
    target = tmp_path / "configured-target"
    target.mkdir()
    sentinel = target / "sentinel"
    sentinel.write_bytes(b"unchanged")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)
    original_verify = AnchoredDirectory.verify
    calls = 0

    def replace_before_write(self: AnchoredDirectory, *, description: str) -> None:
        nonlocal calls
        if description == "content-addressed-cache":
            calls += 1
            if calls == 2:
                component = {
                    "var": project / "var",
                    "cache": project / "var" / "cache",
                    "source-cache": cache / "local",
                }[replaced]
                detached = component.with_name(component.name + "-detached")
                component.rename(detached)
                component.symlink_to(target, target_is_directory=True)
        original_verify(self, description=description)

    monkeypatch.setattr(AnchoredDirectory, "verify", replace_before_write)

    with pytest.raises(SourceError, match="cache.*identity-changed"):
        resolve_sources(config_for(source), cache)

    assert sentinel.read_bytes() == b"unchanged"
    assert tuple(target.iterdir()) == (sentinel,)


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

    def compete(
        staging: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert src_dir_fd is not None
        assert src_dir_fd == dst_dir_fd
        cache_destination = tmp_path / "cache" / "local" / os.fsdecode(destination)
        shutil.copytree(source_root, cache_destination, symlinks=True)
        raise OSError(race_errno, "competing directory")

    monkeypatch.setattr(source_store.os, "rename", compete)

    resolved = resolve_sources(config_for(source), tmp_path / "cache")

    assert hash_tree(resolved[0].root) == resolved[0].revision
    assert not tuple((tmp_path / "cache" / "local").glob(".snapshot-*"))


def test_cache_race_wraps_concurrent_corrupt_directory_and_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "skills/one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)

    def compete(
        staging: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert src_dir_fd is not None
        assert src_dir_fd == dst_dir_fd
        cache_destination = tmp_path / "cache" / "local" / os.fsdecode(destination)
        cache_destination.mkdir()
        (cache_destination / "corrupt").write_text("wrong", encoding="utf-8")
        raise OSError(errno.ENOTEMPTY, "competing directory")

    monkeypatch.setattr(source_store.os, "rename", compete)

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


def _different_lock(lock: SkillLock) -> SkillLock:
    source = lock.sources[0]
    return replace(lock, sources=(replace(source, tree_hash="f" * 64),))


def test_post_commit_directory_fsync_failure_accepts_exact_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    lock = build_lock(config_for(source), resolve_sources(config_for(source), tmp_path / "cache"))
    path = tmp_path / "skill-lock.yaml"
    write_lock_atomic(path, lock)
    candidate = _different_lock(lock)
    candidate_bytes = serialize_lock(candidate)
    original_fsync = os.fsync
    candidate_inode = 0

    def fail_directory_fsync(fd: int) -> None:
        nonlocal candidate_inode
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            candidate_inode = path.stat().st_ino
            raise OSError("injected post-commit failure")
        original_fsync(fd)

    monkeypatch.setattr(os, "fsync", fail_directory_fsync)

    write_lock_atomic(path, candidate)

    assert path.read_bytes() == candidate_bytes
    assert path.stat().st_ino == candidate_inode
    assert not tuple(tmp_path.glob(".skill-lock.yaml.*"))


def test_initial_post_commit_directory_fsync_failure_accepts_exact_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    lock = build_lock(config_for(source), resolve_sources(config_for(source), tmp_path / "cache"))
    path = tmp_path / "skill-lock.yaml"
    candidate_bytes = serialize_lock(lock)
    original_fsync = os.fsync
    candidate_inode = 0

    def fail_directory_fsync(fd: int) -> None:
        nonlocal candidate_inode
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            candidate_inode = path.stat().st_ino
            raise OSError("injected post-commit failure")
        original_fsync(fd)

    monkeypatch.setattr(os, "fsync", fail_directory_fsync)

    write_lock_atomic(path, lock)

    assert path.read_bytes() == candidate_bytes
    assert path.stat().st_ino == candidate_inode


@pytest.mark.parametrize("initially_absent", (False, True))
def test_post_commit_concurrent_same_bytes_new_inode_is_preserved_as_unsafe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, initially_absent: bool
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    lock = build_lock(config_for(source), resolve_sources(config_for(source), tmp_path / "cache"))
    path = tmp_path / "skill-lock.yaml"
    candidate = lock
    if not initially_absent:
        write_lock_atomic(path, lock)
        candidate = _different_lock(lock)
    candidate_bytes = serialize_lock(candidate)
    original_fsync = os.fsync
    concurrent_inode = 0

    def compete_then_fail(fd: int) -> None:
        nonlocal concurrent_inode
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            concurrent = tmp_path / "concurrent"
            concurrent.write_bytes(candidate_bytes)
            os.replace(concurrent, path)
            concurrent_inode = path.stat().st_ino
            raise OSError("injected post-commit failure")
        original_fsync(fd)

    monkeypatch.setattr(os, "fsync", compete_then_fail)

    with pytest.raises(SourceError, match="lock-rollback-unsafe"):
        write_lock_atomic(path, candidate)

    assert path.read_bytes() == candidate_bytes
    assert path.stat().st_ino == concurrent_inode


@pytest.mark.parametrize("initially_absent", (False, True))
def test_concurrent_replacement_at_prior_rollback_boundary_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, initially_absent: bool
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    lock = build_lock(config_for(source), resolve_sources(config_for(source), tmp_path / "cache"))
    path = tmp_path / "skill-lock.yaml"
    candidate = lock
    if not initially_absent:
        write_lock_atomic(path, lock)
        candidate = _different_lock(lock)
    candidate_bytes = serialize_lock(candidate)
    original_fsync = os.fsync
    original_observe = lockfile._observe_public_outcome
    concurrent_inode = 0

    def fail_directory_fsync(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("injected post-commit failure")
        original_fsync(fd)

    def compete_before_public_observation(*args, **kwargs):
        nonlocal concurrent_inode
        concurrent = tmp_path / "concurrent"
        concurrent.write_bytes(candidate_bytes)
        os.replace(concurrent, path)
        concurrent_inode = path.stat().st_ino
        return original_observe(*args, **kwargs)

    monkeypatch.setattr(os, "fsync", fail_directory_fsync)
    monkeypatch.setattr(lockfile, "_observe_public_outcome", compete_before_public_observation)

    with pytest.raises(SourceError, match="lock-rollback-unsafe"):
        write_lock_atomic(path, candidate)

    assert path.read_bytes() == candidate_bytes
    assert path.stat().st_ino == concurrent_inode


@pytest.mark.parametrize("initially_absent", (False, True))
def test_prepublication_fchmod_failure_preserves_exact_prior_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, initially_absent: bool
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    lock = build_lock(config_for(source), resolve_sources(config_for(source), tmp_path / "cache"))
    path = tmp_path / "skill-lock.yaml"
    candidate = lock
    prior: tuple[bytes, int] | None = None
    if not initially_absent:
        write_lock_atomic(path, lock)
        prior = (path.read_bytes(), path.stat().st_ino)
        candidate = _different_lock(lock)

    def fail_fchmod(*_args, **_kwargs) -> None:
        raise OSError("injected prepublication failure")

    monkeypatch.setattr(os, "fchmod", fail_fchmod)

    with pytest.raises(SourceError, match="lock-publication-failed"):
        write_lock_atomic(path, candidate)

    if prior is None:
        assert not path.exists()
    else:
        assert path.read_bytes() == prior[0]
        assert path.stat().st_ino == prior[1]
    assert not tuple(tmp_path.glob(".skill-lock.yaml.*"))


def test_prepublication_stage_close_failure_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    write_skill(source_root, "one")
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("."), None)
    lock = build_lock(config_for(source), resolve_sources(config_for(source), tmp_path / "cache"))
    path = tmp_path / "skill-lock.yaml"
    write_lock_atomic(path, lock)
    prior = (path.read_bytes(), path.stat().st_ino)
    original_close = os.close
    failed = False

    def fail_stage_close(fd: int) -> None:
        nonlocal failed
        if not failed and stat.S_ISREG(os.fstat(fd).st_mode):
            failed = True
            original_close(fd)
            raise OSError("injected stage close failure")
        original_close(fd)

    monkeypatch.setattr(os, "close", fail_stage_close)

    with pytest.raises(SourceError, match="lock-publication-failed"):
        write_lock_atomic(path, _different_lock(lock))

    assert path.read_bytes() == prior[0]
    assert path.stat().st_ino == prior[1]
    assert not tuple(tmp_path.glob(".skill-lock.yaml.*"))
