from __future__ import annotations

import fcntl
import json
import os
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

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


def _desired(root: Path, cache: Path, names: tuple[str, ...]) -> DesiredState:
    links = []
    for name in names:
        source = cache / "source" / "revision" / name
        source.mkdir(parents=True, exist_ok=True)
        (source / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test\n---\n", encoding="utf-8"
        )
        artifact_id = f"source/{name}"
        links.append(
            DesiredLink(
                artifact_id,
                name,
                PurePosixPath(name),
                root / "source" / name,
                hash_tree(source),
                source,
            )
        )
    return DesiredState((DesiredTarget("worker", root, tuple(links)),))


def _plan(root: Path, cache: Path, names: tuple[str, ...]):
    desired = _desired(root, cache, names)
    current = CurrentState((scan_target(TargetSpec("worker", root, ())),), cache)
    return build_plan(desired, current)


def test_create_replace_remove_and_idempotence_preserve_unmanaged(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    root.mkdir()
    sentinel = root / "sentinel.txt"
    sentinel.write_text("never touch", encoding="utf-8")

    first = apply_plan(_plan(root, cache, ("one", "two")), lock_timeout=0.2)
    assert first.changed == 2
    one = root / "source" / "one"
    two = root / "source" / "two"
    assert one.is_symlink() and two.is_symlink()
    assert os.readlink(one) == str(cache / "source" / "revision" / "one")
    assert sentinel.read_text(encoding="utf-8") == "never touch"

    converged = apply_plan(_plan(root, cache, ("one", "two")), lock_timeout=0.2)
    assert converged.changed == 0

    old_one = Path(os.readlink(one))
    replacement = cache / "source" / "revision-2" / "one"
    replacement.mkdir(parents=True)
    (replacement / "SKILL.md").write_text(
        "---\nname: one\ndescription: v2\n---\n", encoding="utf-8"
    )
    desired = DesiredState(
        (
            DesiredTarget(
                "worker",
                root,
                (
                    DesiredLink(
                        "source/one",
                        "one",
                        PurePosixPath("one"),
                        one,
                        hash_tree(replacement),
                        replacement,
                    ),
                ),
            ),
        )
    )
    current = CurrentState((scan_target(TargetSpec("worker", root, ())),), cache)
    result = apply_plan(build_plan(desired, current), lock_timeout=0.2)
    assert result.changed == 2
    assert Path(os.readlink(one)) == replacement
    assert not two.exists() and not two.is_symlink()
    assert old_one != replacement
    assert sentinel.read_text(encoding="utf-8") == "never touch"
    metadata = json.loads((root / ".skill-delegator" / "managed.json").read_text())
    assert [entry["artifact_id"] for entry in metadata["entries"]] == ["source/one"]


def test_existing_relative_managed_link_is_kept_with_exact_raw_target(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    plan = _plan(root, cache, ("one",))
    apply_plan(plan, lock_timeout=0.2)
    link = root / "source" / "one"
    source = cache / "source" / "revision" / "one"
    link.unlink()
    raw = os.path.relpath(source, link.parent)
    link.symlink_to(raw)

    repeat = _plan(root, cache, ("one",))
    assert [operation.action for operation in repeat.operations if operation.artifact_id] == [
        "KEEP"
    ]
    apply_plan(repeat, lock_timeout=0.2)
    assert os.readlink(link) == raw


def test_lock_contention_times_out_without_link_mutation(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    plan = _plan(root, cache, ("one",))
    namespace = root / ".skill-delegator"
    namespace.mkdir(parents=True)
    (namespace / "managed.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manager": "skill-delegator",
                "cache_root": str(cache),
                "entries": [],
            }
        ),
        encoding="utf-8",
    )
    lock_stream = (namespace / "operation.lock").open("a+b")
    fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(ApplyError, match="lock timeout"):
            apply_plan(plan, lock_timeout=0.01)
    finally:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        lock_stream.close()
    assert not (root / "source" / "one").exists()


def test_stale_plan_is_rejected_before_mutation(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    root.mkdir()
    plan = _plan(root, cache, ("one",))
    hostile = root / "appeared.txt"
    hostile.write_text("unmanaged", encoding="utf-8")

    with pytest.raises(ApplyError, match="stale plan"):
        apply_plan(plan, lock_timeout=0.2)

    assert hostile.read_text(encoding="utf-8") == "unmanaged"
    assert not (root / "source" / "one").exists()


def test_blocked_plan_never_mutates(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    root.mkdir()
    occupied = root / "source" / "one"
    occupied.parent.mkdir()
    occupied.write_text("mine", encoding="utf-8")
    plan = _plan(root, cache, ("one",))
    assert plan.blocked

    with pytest.raises(ApplyError, match="blocked"):
        apply_plan(plan, lock_timeout=0.2)
    assert occupied.read_text(encoding="utf-8") == "mine"


def test_internally_inconsistent_reviewed_plan_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    plan = _plan(root, cache, ("one",))
    operation = replace(plan.operations[0], desired_source_path=tmp_path / "other")

    with pytest.raises(ApplyError, match="inconsistent"):
        apply_plan(replace(plan, operations=(operation,)), lock_timeout=0.2)

    assert not (root / "source" / "one").exists()
