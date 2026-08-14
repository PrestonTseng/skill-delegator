"""Deterministic, read-only reconciliation planning."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path, PurePosixPath

from skill_delegator.managed_state import target_fingerprint
from skill_delegator.models import (
    CurrentState,
    DesiredState,
    ManagedEntry,
    PlanOperation,
    PlanTarget,
    ReconciliationPlan,
)

_MUTATIONS = {"CREATE", "REPLACE", "REMOVE"}


def _source_is_safe(path: Path | None) -> bool:
    if path is None or not path.is_absolute():
        return False
    normalized = Path(os.path.abspath(path))
    current = Path(normalized.anchor)
    try:
        for part in normalized.parts[1:]:
            current /= part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                return False
        return stat.S_ISDIR(normalized.lstat().st_mode)
    except OSError:
        return False


def _operation_key(operation: PlanOperation) -> tuple[str, str, str, str]:
    order = {
        "CREATE": "0",
        "REPLACE": "1",
        "REMOVE": "2",
        "KEEP": "3",
        "PRESERVE_UNMANAGED": "4",
    }
    return (
        operation.target_id,
        operation.relative_path.as_posix(),
        order[operation.action],
        operation.artifact_id or "",
    )


def build_plan(desired: DesiredState, current: CurrentState) -> ReconciliationPlan:
    """Compare immutable desired/current state without mutating either filesystem tree."""

    desired_targets = {target.id: target for target in desired.targets}
    current_targets = {target.id: target for target in current.targets}
    blockers: list[str] = []
    if len(desired_targets) != len(desired.targets):
        blockers.append("desired state contains duplicate target ids")
    if len(current_targets) != len(current.targets):
        blockers.append("current state contains duplicate target ids")
    missing = sorted(set(desired_targets) - set(current_targets))
    extra = sorted(set(current_targets) - set(desired_targets))
    if missing or extra:
        blockers.append(f"desired/current target sets differ: missing={missing}, extra={extra}")

    operations: list[PlanOperation] = []
    plan_targets: list[PlanTarget] = []
    for target_id in sorted(set(desired_targets) & set(current_targets)):
        desired_target = desired_targets[target_id]
        current_target = current_targets[target_id]
        desired_root = Path(os.path.abspath(desired_target.root))
        current_root = Path(os.path.abspath(current_target.root))
        if desired_root != current_root:
            blockers.append(
                f"target {target_id} root differs: desired={desired_root}, current={current_root}"
            )
            continue
        expected_cache_root = (
            Path(os.path.abspath(current.expected_cache_root))
            if current.expected_cache_root is not None
            else None
        )
        if expected_cache_root is not None:
            desired_entries = tuple(
                ManagedEntry(
                    link.artifact_id,
                    PurePosixPath(link.artifact_id),
                    link.expected_source_path,
                    link.content_sha256,
                )
                for link in sorted(desired_target.links, key=lambda item: item.artifact_id)
                if link.expected_source_path is not None
            )
            plan_targets.append(
                PlanTarget(
                    target_id,
                    desired_root,
                    expected_cache_root,
                    target_fingerprint(current_target),
                    desired_entries,
                )
            )
        if (
            expected_cache_root is not None
            and current_target.cache_root is not None
            and current_target.cache_root != expected_cache_root
        ):
            blockers.append(
                f"target {target_id} manager cache root differs from locked cache root: "
                f"{current_target.cache_root}"
            )
        desired_links = {link.artifact_id: link for link in desired_target.links}
        managed = {entry.artifact_id: entry for entry in current_target.managed}
        if len(desired_links) != len(desired_target.links):
            blockers.append(f"target {target_id} desired state contains duplicate artifact ids")
        desired_ids = sorted(desired_links)
        for index, artifact_id in enumerate(desired_ids):
            artifact_path = PurePosixPath(artifact_id)
            for descendant_id in desired_ids[index + 1 :]:
                descendant_path = PurePosixPath(descendant_id)
                if descendant_path.is_relative_to(artifact_path):
                    blockers.append(
                        f"target {target_id} desired link {artifact_id} is an ancestor of "
                        f"{descendant_id}"
                    )
        if len(managed) != len(current_target.managed):
            blockers.append(
                f"target {target_id} current state contains duplicate managed artifacts"
            )
        if expected_cache_root is not None:
            for artifact_id, entry in sorted(managed.items()):
                if (
                    not entry.source_path.is_relative_to(expected_cache_root)
                    or entry.source_path == expected_cache_root
                ):
                    blockers.append(
                        f"target {target_id} managed source for {artifact_id} is outside locked "
                        f"cache root: {entry.source_path}"
                    )
        unmanaged = {entry.relative_path: entry for entry in current_target.unmanaged}
        for entry in current_target.unmanaged:
            operations.append(
                PlanOperation(
                    "PRESERVE_UNMANAGED",
                    target_id,
                    None,
                    entry.relative_path,
                    entry_kind=entry.kind,
                )
            )

        for artifact_id in sorted(desired_links):
            link = desired_links[artifact_id]
            expected_relative = PurePosixPath(artifact_id)
            expected_target = desired_root.joinpath(*expected_relative.parts)
            if Path(os.path.abspath(link.target_path)) != expected_target:
                blockers.append(
                    f"target {target_id} desired path is inconsistent for {artifact_id}: "
                    f"{link.target_path}"
                )
                continue
            source = link.expected_source_path
            if not _source_is_safe(source):
                blockers.append(f"desired source path is unavailable or unsafe: {source}")
                continue
            assert source is not None
            if expected_cache_root is not None and (
                not source.is_relative_to(expected_cache_root) or source == expected_cache_root
            ):
                blockers.append(f"desired source path is outside locked cache root: {source}")
                continue
            unmanaged_collision = unmanaged.get(expected_relative)
            if unmanaged_collision is not None:
                blockers.append(
                    f"target {target_id} desired path {expected_relative.as_posix()} is occupied "
                    f"by an unmanaged {unmanaged_collision.kind}"
                )
                continue
            unsafe_parent = next(
                (
                    (PurePosixPath(*expected_relative.parts[:length]), unmanaged[parent])
                    for length in range(1, len(expected_relative.parts))
                    if (parent := PurePosixPath(*expected_relative.parts[:length])) in unmanaged
                    and unmanaged[parent].kind != "directory"
                ),
                None,
            )
            if unsafe_parent is not None:
                parent_path, parent_entry = unsafe_parent
                blockers.append(
                    f"target {target_id} desired path {expected_relative.as_posix()} has unmanaged "
                    f"{parent_entry.kind} parent {parent_path.as_posix()}"
                )
                continue
            existing = managed.get(artifact_id)
            if existing is None:
                operations.append(
                    PlanOperation(
                        "CREATE",
                        target_id,
                        artifact_id,
                        expected_relative,
                        desired_source_path=source,
                    )
                )
            elif existing.relative_path != expected_relative:
                blockers.append(
                    f"target {target_id} managed path is inconsistent for {artifact_id}: "
                    f"{existing.relative_path}"
                )
            elif existing.source_path == source and existing.content_sha256 == link.content_sha256:
                operations.append(
                    PlanOperation(
                        "KEEP",
                        target_id,
                        artifact_id,
                        expected_relative,
                        current_source_path=existing.source_path,
                        desired_source_path=source,
                    )
                )
            else:
                operations.append(
                    PlanOperation(
                        "REPLACE",
                        target_id,
                        artifact_id,
                        expected_relative,
                        current_source_path=existing.source_path,
                        desired_source_path=source,
                    )
                )
        for artifact_id in sorted(set(managed) - set(desired_links)):
            entry = managed[artifact_id]
            operations.append(
                PlanOperation(
                    "REMOVE",
                    target_id,
                    artifact_id,
                    entry.relative_path,
                    current_source_path=entry.source_path,
                )
            )

    unique_blockers = tuple(sorted(set(blockers)))
    if unique_blockers:
        operations = [operation for operation in operations if operation.action not in _MUTATIONS]
    return ReconciliationPlan(
        tuple(sorted(operations, key=_operation_key)),
        unique_blockers,
        tuple(sorted(plan_targets, key=lambda target: (str(target.root), target.id))),
    )


def _operation_document(operation: PlanOperation) -> dict[str, object]:
    document: dict[str, object] = {
        "action": operation.action,
        "target_id": operation.target_id,
        "path": operation.relative_path.as_posix(),
    }
    if operation.artifact_id is not None:
        document["artifact_id"] = operation.artifact_id
    if operation.entry_kind is not None:
        document["entry_kind"] = operation.entry_kind
    if operation.current_source_path is not None:
        document["current_source_path"] = str(operation.current_source_path)
    if operation.desired_source_path is not None:
        document["desired_source_path"] = str(operation.desired_source_path)
    return document


def plan_json(plan: ReconciliationPlan) -> str:
    """Render canonical JSON with exactly one terminal newline."""

    document = {
        "blocked": list(plan.blocked),
        "operations": [_operation_document(operation) for operation in plan.operations],
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"


def plan_text(plan: ReconciliationPlan) -> str:
    """Render stable human-readable lines with exactly one terminal newline."""

    lines = [f"BLOCKED {blocker}" for blocker in plan.blocked]
    for operation in plan.operations:
        line = (
            f"{operation.action} {operation.target_id} "
            f"{operation.artifact_id or '-'} {operation.relative_path.as_posix()}"
        )
        if operation.current_source_path is not None:
            line += f" current={operation.current_source_path}"
        if operation.desired_source_path is not None:
            line += f" desired={operation.desired_source_path}"
        if operation.entry_kind is not None:
            line += f" kind={operation.entry_kind}"
        lines.append(line)
    if not lines:
        lines.append("CONVERGED")
    return "\n".join(lines) + "\n"
