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


def test_replace_failure_after_staging_removal_retains_backup_for_exact_restoration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, initial = _plan(tmp_path, count=1)
    apply_plan(initial, lock_timeout=0.2)
    link = root / "src" / "skill-0"
    old_raw = os.readlink(link)
    managed = root / ".skill-delegator" / "managed.json"
    old_metadata = managed.read_bytes()

    cache = tmp_path / "cache"
    replacement = cache / "src" / "revision-after-staging-cleanup" / "skill-0"
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
    real_remove = reconciler._remove_transaction_tree
    observed_backup_raw: str | None = None

    def fail_after_staging_removal(transaction, kind: str) -> None:
        nonlocal observed_backup_raw
        real_remove(transaction, kind)
        if kind == "staging" and observed_backup_raw is None:
            backup = Path(f"/proc/self/fd/{transaction.backup_fd}") / "src" / "skill-0"
            observed_backup_raw = os.readlink(backup)
            raise OSError("failure after staging-tree removal")

    monkeypatch.setattr(reconciler, "_remove_transaction_tree", fail_after_staging_removal)
    with pytest.raises(ApplyError, match="failure after staging-tree removal"):
        apply_plan(replacement_plan, lock_timeout=0.2)

    assert observed_backup_raw == old_raw
    assert os.readlink(link) == old_raw
    assert managed.read_bytes() == old_metadata
    assert not (root / ".skill-delegator" / "backup").exists()


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
def test_namespace_replacement_never_redirects_writes_and_restores_uncommitted_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    root = tmp_path / "target"
    root.mkdir()
    root, plan = _plan(tmp_path, count=1)
    namespace = root / ".skill-delegator"
    detached = root / ".skill-delegator.detached"
    reached: list[str] = []

    def replace_namespace(name: str) -> None:
        reached.append(name)
        if name == boundary:
            namespace.rename(detached)
            namespace.mkdir()
            (namespace / "outside-sentinel").write_text("untouched", encoding="utf-8")
            raise OSError(f"namespace replaced at {boundary}")

    monkeypatch.setattr(reconciler, "_checkpoint", replace_namespace)
    with pytest.raises(ApplyError, match=f"namespace replaced at {boundary}"):
        apply_plan(plan, lock_timeout=0.2)

    assert boundary in reached
    assert [path.name for path in namespace.iterdir()] == ["outside-sentinel"]
    assert (namespace / "outside-sentinel").read_text(encoding="utf-8") == "untouched"
    assert not (root / "src" / "skill-0").exists()
    assert not (detached / "managed.json").exists()
    assert (detached / "failure.json").is_file()


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


def test_multi_target_failure_after_second_promotion_restores_exact_preapply_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roots = (tmp_path / "target-a", tmp_path / "target-b")
    cache = tmp_path / "cache"

    def make_plan(revision: str, description: str):
        desired_targets = []
        current_targets = []
        for index, root in enumerate(roots):
            root.mkdir(exist_ok=True)
            source = cache / f"src-{index}" / revision / "one"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                f"---\nname: one\ndescription: {description}\n---\n", encoding="utf-8"
            )
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
        return build_plan(
            DesiredState(tuple(desired_targets)), CurrentState(tuple(current_targets), cache)
        )

    apply_plan(make_plan("revision-1", "original"), lock_timeout=0.2)
    links = tuple(root / f"src-{index}" / "one" for index, root in enumerate(roots))
    managed = tuple(root / ".skill-delegator" / "managed.json" for root in roots)
    old_raw_links = tuple(os.readlink(link) for link in links)
    old_metadata = tuple(path.read_bytes() for path in managed)
    replacement_plan = make_plan("revision-2", "replacement")
    detached_b = tmp_path / "target-b-original"
    reached: list[str] = []

    def replace_second_root_after_both_promotions(name: str) -> None:
        reached.append(name)
        if name == "after-promote-2":
            roots[1].rename(detached_b)
            roots[1].mkdir()
            (roots[1] / "outside-sentinel").write_text("untouched", encoding="utf-8")
            raise OSError("second target replaced after both promotions")

    monkeypatch.setattr(reconciler, "_checkpoint", replace_second_root_after_both_promotions)
    with pytest.raises(ApplyError, match="second target replaced after both promotions"):
        apply_plan(replacement_plan, lock_timeout=0.2)

    assert "after-promote-1" in reached
    assert "after-promote-2" in reached
    assert os.readlink(links[0]) == old_raw_links[0]
    assert managed[0].read_bytes() == old_metadata[0]
    detached_link_b = detached_b / "src-1" / "one"
    detached_managed_b = detached_b / ".skill-delegator" / "managed.json"
    assert os.readlink(detached_link_b) == old_raw_links[1]
    assert detached_managed_b.read_bytes() == old_metadata[1]
    assert [path.name for path in roots[1].iterdir()] == ["outside-sentinel"]
    assert (roots[1] / "outside-sentinel").read_text(encoding="utf-8") == "untouched"
