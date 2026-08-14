from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath

import pytest

from skill_delegator import reconciler
from skill_delegator.inventory import hash_tree
from skill_delegator.managed_state import scan_target
from skill_delegator.models import (
    CurrentState,
    DesiredLink,
    DesiredState,
    DesiredTarget,
    TargetSpec,
)
from skill_delegator.planner import build_plan
from skill_delegator.reconciler import ApplyError, apply_plan


def _plan(tmp_path: Path, count: int = 2):
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    links = []
    for index in range(count):
        name = f"skill-{index}"
        source = cache / "src" / "rev" / name
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\n")
        links.append(
            DesiredLink(
                f"src/{name}",
                name,
                PurePosixPath(name),
                root / "src" / name,
                hash_tree(source),
                source,
            )
        )
    desired = DesiredState((DesiredTarget("worker", root, tuple(links)),))
    current = CurrentState((scan_target(TargetSpec("worker", root, ())),), cache)
    return root, build_plan(desired, current)


@pytest.mark.parametrize("boundary", ["after-stage", "after-promote-1", "before-metadata"])
def test_injected_failure_rolls_back_links_directories_and_managed_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    root, plan = _plan(tmp_path)

    def fail(name: str) -> None:
        if name == boundary:
            raise OSError("injected failure")

    monkeypatch.setattr(reconciler, "_checkpoint", fail)
    with pytest.raises(ApplyError, match="injected failure"):
        apply_plan(plan, lock_timeout=0.2)

    assert not root.exists()


def test_permission_error_during_staging_has_no_partial_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, plan = _plan(tmp_path)

    def deny(source: str | bytes, destination: str | bytes, *args, **kwargs) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(reconciler.os, "symlink", deny)
    with pytest.raises(ApplyError, match="denied"):
        apply_plan(plan, lock_timeout=0.2)
    assert not root.exists()


def test_hostile_target_root_replacement_after_planning_is_never_followed(tmp_path: Path) -> None:
    root, plan = _plan(tmp_path, count=1)
    outside = tmp_path / "outside"
    outside.mkdir()
    root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ApplyError, match="symlink"):
        apply_plan(plan, lock_timeout=0.2)

    assert tuple(outside.iterdir()) == ()


def test_source_cache_tamper_is_rejected_before_promotion(tmp_path: Path) -> None:
    root, plan = _plan(tmp_path, count=1)
    source = plan.targets[0].desired_entries[0].source_path
    (source / "SKILL.md").write_text("tampered")

    with pytest.raises(ApplyError, match="content hash"):
        apply_plan(plan, lock_timeout=0.2)
    assert not (root / "src" / "skill-0").exists()


def test_failed_replace_restores_exact_raw_link_and_metadata_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, initial = _plan(tmp_path, count=1)
    apply_plan(initial, lock_timeout=0.2)
    link = root / "src" / "skill-0"
    old_raw = os.readlink(link)
    managed = root / ".skill-delegator" / "managed.json"
    old_metadata = managed.read_bytes()

    cache = tmp_path / "cache"
    replacement = cache / "src" / "revision-2" / "skill-0"
    replacement.mkdir(parents=True)
    (replacement / "SKILL.md").write_text(
        "---\nname: skill-0\ndescription: replacement\n---\n", encoding="utf-8"
    )
    desired = DesiredState(
        (
            DesiredTarget(
                "worker",
                root,
                (
                    DesiredLink(
                        "src/skill-0",
                        "skill-0",
                        PurePosixPath("skill-0"),
                        link,
                        hash_tree(replacement),
                        replacement,
                    ),
                ),
            ),
        )
    )
    current = CurrentState((scan_target(TargetSpec("worker", root, ())),), cache)
    replacement_plan = build_plan(desired, current)

    def fail(name: str) -> None:
        if name == "after-promote-1":
            raise OSError("replace failed")

    monkeypatch.setattr(reconciler, "_checkpoint", fail)
    with pytest.raises(ApplyError, match="replace failed"):
        apply_plan(replacement_plan, lock_timeout=0.2)

    assert os.readlink(link) == old_raw
    assert managed.read_bytes() == old_metadata


def test_rollback_failure_is_surfaced_and_failure_receipt_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "target"
    root.mkdir()
    root, plan = _plan(tmp_path, count=1)

    def fail(name: str) -> None:
        if name == "after-promote-1":
            raise OSError("primary")

    monkeypatch.setattr(reconciler, "_checkpoint", fail)
    monkeypatch.setattr(
        reconciler, "_rollback_entry", lambda _entry: (_ for _ in ()).throw(OSError("rollback"))
    )

    with pytest.raises(ApplyError, match="rollback failed"):
        apply_plan(plan, lock_timeout=0.2)
    receipt = (root / ".skill-delegator" / "failure.json").read_text()
    assert "rollback" in receipt
    assert len(receipt) < 2048


def test_rollback_never_deletes_destination_replaced_by_unmanaged_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, plan = _plan(tmp_path, count=1)
    final = root / "src" / "skill-0"

    def replace_with_unmanaged(name: str) -> None:
        if name == "after-promote-1":
            final.unlink()
            final.write_text("unmanaged race", encoding="utf-8")
            raise OSError("hostile replacement")

    monkeypatch.setattr(reconciler, "_checkpoint", replace_with_unmanaged)
    with pytest.raises(ApplyError, match="rollback failed"):
        apply_plan(plan, lock_timeout=0.2)

    assert final.read_text(encoding="utf-8") == "unmanaged race"


def test_replacing_lock_namespace_cannot_acquire_second_cooperating_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "target"
    root.mkdir()
    root, plan = _plan(tmp_path, count=1)
    namespace = root / ".skill-delegator"
    original = root / ".skill-delegator.original"
    attempted = False

    def replace_namespace(name: str) -> None:
        nonlocal attempted
        if name != "after-lock" or attempted:
            return
        attempted = True
        namespace.rename(original)
        namespace.mkdir()
        with pytest.raises(ApplyError, match="lock timeout"):
            apply_plan(plan, lock_timeout=0.01)
        raise OSError("namespace replaced")

    monkeypatch.setattr(reconciler, "_checkpoint", replace_namespace)
    with pytest.raises(ApplyError, match="namespace replaced"):
        apply_plan(plan, lock_timeout=0.2)

    assert attempted
    assert not (namespace / "managed.json").exists()
    assert not (root / "src").exists()


@pytest.mark.parametrize(
    "boundary",
    ["after-lock", "after-scan", "after-promote-1", "before-metadata", "after-metadata-1"],
)
def test_root_replacement_never_redirects_transaction_writes_or_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    root = tmp_path / "target"
    root.mkdir()
    root, plan = _plan(tmp_path, count=1)
    detached = tmp_path / "detached-original"

    def replace_root(name: str) -> None:
        if name == boundary:
            root.rename(detached)
            root.mkdir()
            (root / "outside-sentinel").write_text("untouched", encoding="utf-8")
            raise OSError("root replaced")

    monkeypatch.setattr(reconciler, "_checkpoint", replace_root)
    with pytest.raises(ApplyError, match="root replaced"):
        apply_plan(plan, lock_timeout=0.2)

    assert [path.name for path in root.iterdir()] == ["outside-sentinel"]
    assert (root / "outside-sentinel").read_text(encoding="utf-8") == "untouched"
    assert not (detached / "src" / "skill-0").exists()
    assert not (detached / ".skill-delegator" / "managed.json").exists()
    assert (detached / ".skill-delegator" / "failure.json").is_file()


def test_rollback_preserves_same_raw_target_symlink_with_new_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "target"
    root.mkdir()
    root, plan = _plan(tmp_path, count=1)
    final = root / "src" / "skill-0"
    replacement_inode: int | None = None

    def replace_promoted_link(name: str) -> None:
        nonlocal replacement_inode
        if name == "after-promote-1":
            raw = os.readlink(final)
            final.unlink()
            final.symlink_to(raw)
            replacement_inode = final.lstat().st_ino
            raise OSError("same-target replacement")

    monkeypatch.setattr(reconciler, "_checkpoint", replace_promoted_link)
    with pytest.raises(ApplyError, match="rollback failed"):
        apply_plan(plan, lock_timeout=0.2)

    assert final.is_symlink()
    assert final.lstat().st_ino == replacement_inode
    assert os.readlink(final) == str(plan.targets[0].desired_entries[0].source_path)


def test_post_commit_cleanup_failure_keeps_committed_link_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, initial = _plan(tmp_path, count=1)
    apply_plan(initial, lock_timeout=0.2)
    old_link = root / "src" / "skill-0"
    old_raw = os.readlink(old_link)

    cache = tmp_path / "cache"
    replacement = cache / "src" / "revision-2" / "skill-0"
    replacement.mkdir(parents=True)
    (replacement / "SKILL.md").write_text("---\nname: skill-0\ndescription: v2\n---\n")
    desired = DesiredState(
        (
            DesiredTarget(
                "worker",
                root,
                (
                    DesiredLink(
                        "src/skill-0",
                        "skill-0",
                        PurePosixPath("skill-0"),
                        old_link,
                        hash_tree(replacement),
                        replacement,
                    ),
                ),
            ),
        )
    )
    current = CurrentState((scan_target(TargetSpec("worker", root, ())),), cache)
    plan = build_plan(desired, current)

    def fail(name: str) -> None:
        if name == "after-backup-cleanup-1":
            raise OSError("cleanup failed after backup removal")

    monkeypatch.setattr(reconciler, "_checkpoint", fail)
    with pytest.raises(ApplyError, match="committed.*cleanup failed"):
        apply_plan(plan, lock_timeout=0.2)

    assert os.readlink(old_link) == str(replacement)
    assert os.readlink(old_link) != old_raw
    managed = json.loads((root / ".skill-delegator" / "managed.json").read_text())
    assert managed["entries"][0]["source_path"] == str(replacement)


def test_failure_after_metadata_commit_never_rolls_back_initially_absent_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, plan = _plan(tmp_path, count=1)

    def fail(name: str) -> None:
        if name == "after-metadata":
            raise OSError("post-commit failure")

    monkeypatch.setattr(reconciler, "_checkpoint", fail)
    with pytest.raises(ApplyError, match="transaction committed"):
        apply_plan(plan, lock_timeout=0.2)

    link = root / "src" / "skill-0"
    assert link.is_symlink()
    managed = json.loads((root / ".skill-delegator" / "managed.json").read_text())
    assert managed["entries"][0]["artifact_id"] == "src/skill-0"
    assert not (root / ".skill-delegator" / "staging").exists()
    assert not (root / ".skill-delegator" / "backup").exists()


def test_operation_lock_open_failure_restores_initially_absent_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, plan = _plan(tmp_path, count=1)
    real_open = reconciler.os.open

    def deny(path, flags, mode=0o777, *, dir_fd=None):
        if Path(path).name == "operation.lock":
            raise PermissionError("operation lock denied")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(reconciler.os, "open", deny)
    with pytest.raises(ApplyError, match="operation lock denied"):
        apply_plan(plan, lock_timeout=0.2)
    assert not root.exists()


def test_multi_target_partial_failure_restores_every_target_without_replacement_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roots = (tmp_path / "target-a", tmp_path / "target-b")
    cache = tmp_path / "cache"
    desired_targets = []
    current_targets = []
    for index, root in enumerate(roots):
        root.mkdir()
        source = cache / f"src-{index}" / "rev" / "one"
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text("---\nname: one\ndescription: test\n---\n")
        desired_targets.append(
            DesiredTarget(
                f"worker-{index}",
                root,
                (
                    DesiredLink(
                        f"src-{index}/one",
                        "one",
                        PurePosixPath("one"),
                        root / f"src-{index}" / "one",
                        hash_tree(source),
                        source,
                    ),
                ),
            )
        )
        current_targets.append(scan_target(TargetSpec(f"worker-{index}", root, ())))
    plan = build_plan(
        DesiredState(tuple(desired_targets)), CurrentState(tuple(current_targets), cache)
    )
    detached = tmp_path / "target-b-original"

    def fail(name: str) -> None:
        if name == "after-promote-1":
            roots[1].rename(detached)
            roots[1].mkdir()
            (roots[1] / "outside-sentinel").write_text("untouched")
        if name == "after-promote-2":
            raise OSError("multi-target failure")

    monkeypatch.setattr(reconciler, "_checkpoint", fail)
    with pytest.raises(ApplyError, match="target identity changed"):
        apply_plan(plan, lock_timeout=0.2)

    assert not (roots[0] / "src-0" / "one").exists()
    assert not (detached / "src-1" / "one").exists()
    assert [path.name for path in roots[1].iterdir()] == ["outside-sentinel"]
