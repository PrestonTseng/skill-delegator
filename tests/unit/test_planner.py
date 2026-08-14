from __future__ import annotations

from pathlib import Path, PurePosixPath

from skill_delegator.models import (
    CurrentState,
    CurrentTargetState,
    DesiredLink,
    DesiredState,
    DesiredTarget,
    ManagedEntry,
    UnmanagedEntry,
)
from skill_delegator.planner import build_plan, plan_json, plan_text

_SHA = "a" * 64


def _desired(root: Path, source: Path, artifact_id: str = "alpha/tool") -> DesiredState:
    return DesiredState(
        (
            DesiredTarget(
                "worker",
                root,
                (
                    DesiredLink(
                        artifact_id,
                        "tool",
                        PurePosixPath("tool"),
                        root.joinpath(*artifact_id.split("/")),
                        _SHA,
                        source,
                    ),
                ),
            ),
        )
    )


def _current(
    root: Path,
    *,
    managed: tuple[ManagedEntry, ...] = (),
    unmanaged: tuple[UnmanagedEntry, ...] = (),
) -> CurrentState:
    return CurrentState((CurrentTargetState("worker", root, managed, unmanaged),))


def test_plans_create_for_empty_target(tmp_path: Path) -> None:
    source = tmp_path / "cache" / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    plan = build_plan(_desired(tmp_path / "target", source), _current(tmp_path / "target"))

    assert [operation.action for operation in plan.operations] == ["CREATE"]
    assert plan.has_changes
    assert not plan.blocked


def test_plans_keep_for_exact_managed_link(tmp_path: Path) -> None:
    root = tmp_path / "target"
    source = tmp_path / "cache" / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    managed = ManagedEntry("alpha/tool", PurePosixPath("alpha/tool"), source, _SHA)

    plan = build_plan(_desired(root, source), _current(root, managed=(managed,)))

    assert [operation.action for operation in plan.operations] == ["KEEP"]
    assert not plan.has_changes


def test_plans_replace_for_valid_stale_managed_link(tmp_path: Path) -> None:
    root = tmp_path / "target"
    old = tmp_path / "cache" / "alpha" / "old" / "tool"
    new = tmp_path / "cache" / "alpha" / "new" / "tool"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    managed = ManagedEntry("alpha/tool", PurePosixPath("alpha/tool"), old, "b" * 64)

    plan = build_plan(_desired(root, new), _current(root, managed=(managed,)))

    assert [operation.action for operation in plan.operations] == ["REPLACE"]
    assert plan.operations[0].current_source_path == old
    assert plan.operations[0].desired_source_path == new


def test_remove_references_only_recorded_manager_owned_entries(tmp_path: Path) -> None:
    root = tmp_path / "target"
    old = tmp_path / "cache" / "alpha" / "old" / "tool"
    old.mkdir(parents=True)
    managed = ManagedEntry("alpha/tool", PurePosixPath("alpha/tool"), old, _SHA)

    plan = build_plan(
        DesiredState((DesiredTarget("worker", root, ()),)), _current(root, managed=(managed,))
    )

    assert [operation.action for operation in plan.operations] == ["REMOVE"]
    assert plan.operations[0].artifact_id == "alpha/tool"


def test_preserves_unmanaged_entries_and_blocks_desired_collision(tmp_path: Path) -> None:
    root = tmp_path / "target"
    source = tmp_path / "cache" / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    unmanaged = (
        UnmanagedEntry(PurePosixPath("notes"), "directory", None),
        UnmanagedEntry(PurePosixPath("alpha/tool"), "file", None),
    )

    plan = build_plan(_desired(root, source), _current(root, unmanaged=unmanaged))

    assert [operation.action for operation in plan.operations] == [
        "PRESERVE_UNMANAGED",
        "PRESERVE_UNMANAGED",
    ]
    assert plan.blocked == (
        "target worker desired path alpha/tool is occupied by an unmanaged file",
    )
    assert not any(
        operation.action in {"CREATE", "REPLACE", "REMOVE"} for operation in plan.operations
    )


def test_blocks_unmanaged_non_directory_parent_and_nested_desired_links(tmp_path: Path) -> None:
    root = tmp_path / "target"
    source = tmp_path / "cache" / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    parent_collision = build_plan(
        _desired(root, source),
        _current(
            root,
            unmanaged=(
                Unmounted := UnmanagedEntry(PurePosixPath("alpha"), "symlink", "elsewhere"),
            ),
        ),
    )
    assert parent_collision.blocked == (
        "target worker desired path alpha/tool has unmanaged symlink parent alpha",
    )
    assert parent_collision.operations[0].entry_kind == Unmounted.kind

    child = DesiredLink(
        "alpha/tool/child",
        "child",
        PurePosixPath("tool/child"),
        root / "alpha/tool/child",
        _SHA,
        source,
    )
    base = _desired(root, source).targets[0]
    nested = build_plan(
        DesiredState((DesiredTarget(base.id, base.root, (*base.links, child)),)),
        _current(root),
    )
    assert nested.blocked == (
        "target worker desired link alpha/tool is an ancestor of alpha/tool/child",
    )


def test_planner_rejects_missing_or_symlinked_expected_source(tmp_path: Path) -> None:
    root = tmp_path / "target"
    missing = tmp_path / "cache" / "alpha" / "rev" / "missing"
    missing_plan = build_plan(_desired(root, missing), _current(root))
    assert missing_plan.blocked == (f"desired source path is unavailable or unsafe: {missing}",)

    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "cache" / "alpha" / "rev" / "tool"
    linked.parent.mkdir(parents=True)
    linked.symlink_to(real, target_is_directory=True)
    linked_plan = build_plan(_desired(root, linked), _current(root))
    assert linked_plan.blocked == (f"desired source path is unavailable or unsafe: {linked}",)


def test_plan_rendering_is_byte_repeatable_and_ordered(tmp_path: Path) -> None:
    root = tmp_path / "target"
    source = tmp_path / "cache" / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    plan = build_plan(
        _desired(root, source),
        _current(root, unmanaged=(UnmanagedEntry(PurePosixPath("z-last"), "file", None),)),
    )

    assert plan_json(plan) == plan_json(plan)
    assert plan_text(plan) == plan_text(plan)
    assert plan_json(plan).endswith("\n")
    assert plan_text(plan).endswith("\n")
    assert '"action":"CREATE"' in plan_json(plan)
    assert "CREATE worker alpha/tool" in plan_text(plan)
