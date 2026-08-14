from __future__ import annotations

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

from skill_delegator.errors import SourceError
from skill_delegator.lockfile import build_lock
from skill_delegator.models import AuthorityConfig, PoolSpec, SourceSpec, TargetSpec
from skill_delegator.source_store import resolve_sources
from skill_delegator.updater import check_updates, prepare_update, proposal_json, proposal_text


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def write_skill(root: Path, relative: str, body: str = "body", name: str | None = None) -> None:
    directory = root / "skills" / relative
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name or relative}\ndescription: fixture\n---\n{body}\n", encoding="utf-8"
    )


def commit(repo: Path, message: str) -> str:
    git(repo, "add", ".")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


def git_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    work = tmp_path / "work"
    bare = tmp_path / "remote.git"
    work.mkdir(parents=True)
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "user.email", "test@example.invalid")
    git(work, "config", "user.name", "Test")
    write_skill(work, "pooled", "one")
    first = commit(work, "first")
    git(tmp_path, "init", "--bare", "-q", str(bare))
    git(work, "remote", "add", "origin", str(bare))
    git(work, "push", "-q", "-u", "origin", "main")
    return work, bare, first


def authority(
    tmp_path: Path,
    sources: tuple[SourceSpec, ...],
    *,
    pool: tuple[str, ...] = ("upstream/pooled",),
    grants: tuple[str, ...] = ("upstream/pooled",),
) -> AuthorityConfig:
    return AuthorityConfig(
        "test",
        True,
        "none",
        sources,
        tuple(PoolSpec(item) for item in pool),
        (TargetSpec("worker", tmp_path / "target", grants),) if grants else (),
        cache_root=tmp_path / "cache",
    )


def locked(config: AuthorityConfig):
    assert config.cache_root is not None
    return build_lock(config, resolve_sources(config, config.cache_root))


def test_check_reports_no_change_then_fast_forward_without_changing_lock(tmp_path: Path) -> None:
    work, bare, _ = git_fixture(tmp_path)
    source = SourceSpec("upstream", "git", str(bare), PurePosixPath("skills"), "main")
    config = authority(tmp_path, (source,))
    old = locked(config)

    assert check_updates(config, old)[0].relation == "no-change"
    old_bytes = repr(old)
    write_skill(work, "pooled", "two")
    second = commit(work, "second")
    git(work, "push", "-q", "origin", "main")

    update = check_updates(config, old)[0]
    assert update.old_revision == old.sources[0].resolved_commit
    assert update.new_revision == second
    assert update.relation == "fast-forward"
    assert repr(old) == old_bytes


def test_check_reports_tag_movement_and_force_moved_branch(tmp_path: Path) -> None:
    work, bare, first = git_fixture(tmp_path)
    git(work, "tag", "v1", first)
    git(work, "push", "-q", "origin", "v1")
    tag_source = SourceSpec("upstream", "git", str(bare), PurePosixPath("skills"), "refs/tags/v1")
    tag_config = authority(tmp_path, (tag_source,))
    tag_lock = locked(tag_config)
    write_skill(work, "pooled", "tag-two")
    second = commit(work, "second")
    git(work, "tag", "-f", "v1", second)
    git(work, "push", "-q", "--force", "origin", "v1")
    assert check_updates(tag_config, tag_lock)[0].relation == "tag-moved"

    branch_source = replace(tag_source, track="main")
    branch_config = authority(tmp_path, (branch_source,))
    branch_lock = locked(branch_config)
    git(work, "checkout", "-q", "--orphan", "rewritten")
    git(work, "rm", "-q", "-r", "-f", ".")
    write_skill(work, "pooled", "rewrite")
    rewritten = commit(work, "rewrite")
    git(work, "push", "-q", "--force", "origin", f"{rewritten}:main")
    assert check_updates(branch_config, branch_lock)[0].relation in {"diverged", "force-moved"}


def test_prepare_update_preserves_other_source_and_reports_bounded_artifact_diffs(
    tmp_path: Path,
) -> None:
    work, bare, _ = git_fixture(tmp_path)
    write_skill(work, "stable", "stable")
    commit(work, "stable")
    git(work, "push", "-q", "origin", "main")
    local = tmp_path / "local"
    write_skill(local, "fixed", "fixed")
    sources = (
        SourceSpec("upstream", "git", str(bare), PurePosixPath("skills"), "main"),
        SourceSpec("local", "filesystem", local, PurePosixPath("skills")),
    )
    config = authority(
        tmp_path,
        sources,
        pool=("upstream/pooled", "upstream/stable", "local/fixed"),
    )
    old = locked(config)
    old_local = next(item for item in old.sources if item.source_id == "local")
    write_skill(local, "fixed", "silently moved")
    write_skill(work, "pooled", "changed")
    write_skill(work, "new", "new")
    commit(work, "update")
    git(work, "push", "-q", "origin", "main")

    proposal = prepare_update("upstream", config, old)

    assert (
        next(item for item in proposal.candidate_lock.sources if item.source_id == "local")
        == old_local
    )
    assert [(item.canonical_id, item.status) for item in proposal.artifacts] == [
        ("upstream/pooled", "changed"),
        ("upstream/stable", "unchanged"),
    ]
    assert proposal.new_ungranted == ("upstream/new",)
    assert "body" not in proposal_text(proposal)
    assert proposal_json(proposal) == proposal_json(proposal)
    assert proposal_text(proposal) == proposal_text(proposal)


def test_prepare_update_blocks_deleted_or_renamed_grant_but_allows_ungranted_removal(
    tmp_path: Path,
) -> None:
    work, bare, _ = git_fixture(tmp_path)
    source = SourceSpec("upstream", "git", str(bare), PurePosixPath("skills"), "main")
    config = authority(tmp_path, (source,))
    write_skill(work, "unused", "unused")
    commit(work, "unused")
    git(work, "push", "-q", "origin", "main")
    old = locked(config)
    (work / "skills" / "unused" / "SKILL.md").unlink()
    (work / "skills" / "unused").rmdir()
    commit(work, "remove unused")
    git(work, "push", "-q", "origin", "main")
    proposal = prepare_update("upstream", config, old)
    assert proposal.removed_ungranted == ("upstream/unused",)

    (work / "skills" / "pooled").rename(work / "skills" / "renamed")
    commit(work, "rename grant")
    git(work, "push", "-q", "origin", "main")
    with pytest.raises(SourceError, match="candidate-invalid"):
        prepare_update("upstream", config, old)


def test_filesystem_movement_and_offline_git_are_deterministic(tmp_path: Path) -> None:
    local = tmp_path / "local"
    write_skill(local, "one")
    fs = SourceSpec("local", "filesystem", local, PurePosixPath("skills"))
    config = authority(tmp_path, (fs,), pool=(), grants=())
    old = locked(config)
    assert check_updates(config, old)[0].relation == "no-change"
    write_skill(local, "two")
    assert check_updates(config, old)[0].relation == "filesystem-moved"

    _, bare, _ = git_fixture(tmp_path / "offline")
    missing = SourceSpec("upstream", "git", str(bare), PurePosixPath("skills"), "main")
    offline_config = authority(tmp_path / "offline", (missing,))
    offline_lock = locked(offline_config)
    shutil.rmtree(bare)
    unavailable = check_updates(offline_config, offline_lock)[0]
    assert unavailable.relation == "unavailable"
    assert unavailable.new_revision is None


def test_corrupt_old_lock_and_unknown_selected_source_fail_closed(tmp_path: Path) -> None:
    _, bare, _ = git_fixture(tmp_path)
    source = SourceSpec("upstream", "git", str(bare), PurePosixPath("skills"), "main")
    config = authority(tmp_path, (source,))
    old = locked(config)
    corrupt = replace(old, sources=(replace(old.sources[0], resolved_commit="bad"),))
    with pytest.raises(SourceError, match="invalid locked identity"):
        check_updates(config, corrupt)
    with pytest.raises(SourceError, match="unknown source"):
        prepare_update("missing", config, old)
