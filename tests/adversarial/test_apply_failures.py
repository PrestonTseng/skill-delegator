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


@pytest.mark.parametrize(
    "boundary", ["after-stage", "after-promote-1", "before-metadata", "after-metadata"]
)
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

    assert not (root / "src" / "skill-0").exists()
    assert not (root / "src" / "skill-1").exists()
    assert not (root / ".skill-delegator" / "managed.json").exists()
    receipt = json.loads((root / ".skill-delegator" / "failure.json").read_text())
    assert receipt["status"] == "failed"
    assert len(json.dumps(receipt)) < 2048


def test_permission_error_during_staging_has_no_partial_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, plan = _plan(tmp_path)
    real_symlink = os.symlink

    def deny(source: str | bytes, destination: str | bytes, *args, **kwargs) -> None:
        if ".skill-delegator" in os.fsdecode(destination):
            raise PermissionError("denied")
        real_symlink(source, destination, *args, **kwargs)

    monkeypatch.setattr(reconciler.os, "symlink", deny)
    with pytest.raises(ApplyError, match="denied"):
        apply_plan(plan, lock_timeout=0.2)
    assert not (root / "src").exists()


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
