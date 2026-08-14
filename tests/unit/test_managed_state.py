from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_delegator.managed_state import TargetStateError, scan_target
from skill_delegator.models import TargetSpec

_SHA = "a" * 64


def _target(root: Path) -> TargetSpec:
    return TargetSpec("worker", root, ())


def _managed(root: Path, cache_root: Path, entries: list[dict[str, str]]) -> None:
    metadata = root / ".skill-delegator"
    metadata.mkdir(parents=True)
    (metadata / "managed.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manager": "skill-delegator",
                "cache_root": str(cache_root),
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )


def _entry(artifact_id: str, source_path: Path) -> dict[str, str]:
    return {
        "artifact_id": artifact_id,
        "source_path": str(source_path),
        "content_sha256": _SHA,
    }


def test_absent_and_empty_roots_scan_as_empty(tmp_path: Path) -> None:
    absent = scan_target(_target(tmp_path / "absent"))
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    empty = scan_target(_target(empty_root))

    assert absent.managed == empty.managed == ()
    assert absent.unmanaged == empty.unmanaged == ()


def test_scans_correct_managed_link_and_preserves_unmanaged_kinds(tmp_path: Path) -> None:
    root = tmp_path / "target"
    source = tmp_path / "cache" / "alpha" / "revision" / "skills" / "tool"
    source.mkdir(parents=True)
    (root / "alpha" / "skills").mkdir(parents=True)
    (root / "alpha" / "skills" / "tool").symlink_to(source)
    (root / "note.txt").write_text("keep", encoding="utf-8")
    (root / "folder").mkdir()
    (root / "external").symlink_to(tmp_path / "elsewhere")
    _managed(root, tmp_path / "cache", [_entry("alpha/skills/tool", source)])

    state = scan_target(_target(root))

    assert state.managed[0].artifact_id == "alpha/skills/tool"
    assert state.managed[0].source_path == source
    unmanaged = {(entry.relative_path.as_posix(), entry.kind) for entry in state.unmanaged}
    assert ("note.txt", "file") in unmanaged
    assert ("folder", "directory") in unmanaged
    assert ("external", "symlink") in unmanaged


@pytest.mark.parametrize(
    "document",
    [
        "{",
        '{"schema_version":1,"schema_version":1,"manager":"skill-delegator","cache_root":"/tmp/cache","entries":[]}',
        '{"schema_version":2,"manager":"skill-delegator","cache_root":"/tmp/cache","entries":[]}',
        '{"schema_version":1,"manager":"other","cache_root":"/tmp/cache","entries":[]}',
        '{"schema_version":1,"manager":"skill-delegator","cache_root":"relative","entries":[]}',
        '{"schema_version":1,"manager":"skill-delegator","cache_root":"/tmp/cache","entries":[],"extra":true}',
    ],
)
def test_malformed_or_ambiguously_owned_metadata_fails_closed(
    tmp_path: Path, document: str
) -> None:
    root = tmp_path / "target"
    metadata = root / ".skill-delegator"
    metadata.mkdir(parents=True)
    (metadata / "managed.json").write_text(document, encoding="utf-8")

    with pytest.raises(TargetStateError):
        scan_target(_target(root))


def test_duplicate_managed_artifact_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "target"
    source = tmp_path / "cache" / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    _managed(root, tmp_path / "cache", [_entry("alpha/tool", source)] * 2)

    with pytest.raises(TargetStateError, match="duplicate managed artifact"):
        scan_target(_target(root))


@pytest.mark.parametrize("component", ["root", "metadata", "managed"])
def test_symlinked_root_or_metadata_components_fail_closed(tmp_path: Path, component: str) -> None:
    real = tmp_path / "real"
    real.mkdir()
    root = tmp_path / "target"
    if component == "root":
        root.symlink_to(real, target_is_directory=True)
    elif component == "metadata":
        root.mkdir()
        (root / ".skill-delegator").symlink_to(real, target_is_directory=True)
    else:
        metadata = root / ".skill-delegator"
        metadata.mkdir(parents=True)
        actual = tmp_path / "actual.json"
        actual.write_text("{}", encoding="utf-8")
        (metadata / "managed.json").symlink_to(actual)

    with pytest.raises(TargetStateError, match="symlink"):
        scan_target(_target(root))


def test_dangling_root_and_broken_managed_link_fail_closed(tmp_path: Path) -> None:
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "missing", target_is_directory=True)
    with pytest.raises(TargetStateError):
        scan_target(_target(dangling))

    root = tmp_path / "target"
    source = tmp_path / "cache" / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    (root / "alpha").mkdir(parents=True)
    (root / "alpha" / "tool").symlink_to(tmp_path / "gone")
    _managed(root, tmp_path / "cache", [_entry("alpha/tool", source)])
    with pytest.raises(TargetStateError, match="broken managed link"):
        scan_target(_target(root))


def test_managed_link_mismatch_and_cache_escape_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    source = cache / "alpha" / "rev" / "tool"
    wrong = cache / "alpha" / "other" / "tool"
    source.mkdir(parents=True)
    wrong.mkdir(parents=True)
    (root / "alpha").mkdir(parents=True)
    (root / "alpha" / "tool").symlink_to(wrong)
    _managed(root, cache, [_entry("alpha/tool", source)])
    with pytest.raises(TargetStateError, match="does not match manager metadata"):
        scan_target(_target(root))

    root2 = tmp_path / "target2"
    outside = tmp_path / "outside"
    outside.mkdir()
    (root2 / "alpha").mkdir(parents=True)
    (root2 / "alpha" / "tool").symlink_to(outside)
    _managed(root2, cache, [_entry("alpha/tool", outside)])
    with pytest.raises(TargetStateError, match="outside manager cache root"):
        scan_target(_target(root2))


def test_symlinked_managed_parent_component_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "target"
    cache = tmp_path / "cache"
    source = cache / "alpha" / "rev" / "tool"
    source.mkdir(parents=True)
    actual_parent = tmp_path / "actual-parent"
    actual_parent.mkdir()
    (actual_parent / "tool").symlink_to(source)
    root.mkdir()
    (root / "alpha").symlink_to(actual_parent, target_is_directory=True)
    _managed(root, cache, [_entry("alpha/tool", source)])

    with pytest.raises(TargetStateError, match="symlinked managed path component"):
        scan_target(_target(root))
