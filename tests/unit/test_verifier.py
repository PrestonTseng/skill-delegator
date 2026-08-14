from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath

import pytest

from skill_delegator import verifier
from skill_delegator.inventory import hash_tree
from skill_delegator.models import (
    CurrentState,
    DesiredLink,
    DesiredSource,
    DesiredState,
    DesiredTarget,
)
from skill_delegator.verifier import _read_config_input, _repository_commit, verify_state


def _fixture(
    tmp_path: Path, *, runtime_name: str = "one"
) -> tuple[DesiredState, CurrentState, Path, Path]:
    cache = tmp_path / "var" / "cache" / "sources"
    source = cache / "source" / "revision" / "skills" / "one"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text(
        f"---\nname: {runtime_name}\ndescription: fixture\n---\nbody\n", encoding="utf-8"
    )
    target = tmp_path / "target"
    link = target / "source" / "one"
    link.parent.mkdir(parents=True)
    link.symlink_to(source)
    namespace = target / ".skill-delegator"
    namespace.mkdir()
    digest = hash_tree(source)
    (namespace / "managed.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manager": "skill-delegator",
                "cache_root": str(cache),
                "entries": [
                    {
                        "artifact_id": "source/one",
                        "source_path": str(source),
                        "content_sha256": digest,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    desired = DesiredState(
        (
            DesiredTarget(
                "worker",
                target,
                (
                    DesiredLink(
                        "source/one",
                        runtime_name,
                        PurePosixPath("skills/one"),
                        link,
                        digest,
                        source,
                    ),
                ),
            ),
        )
    )
    return desired, CurrentState((), cache), target, source


def test_fresh_converged_state_records_verified_links_and_fingerprint(tmp_path: Path) -> None:
    desired, current, _, _ = _fixture(tmp_path)

    result = verify_state(desired, current)

    assert result.result == "converged"
    assert result.converged
    assert result.reasons == ()
    assert result.operation_summary.desired_links == 1
    assert result.operation_summary.verified_links == 1
    assert len(result.target_fingerprints) == 1
    assert len(result.target_fingerprints[0].sha256) == 64


def test_config_read_retains_ancestor_inodes_and_disables_stale_repository_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    config = project / "config"
    config.mkdir(parents=True)
    expected = b"retained original bytes"
    (config / "authority.yaml").write_bytes(expected)
    external = tmp_path / "external-config"
    external.mkdir()
    (external / "authority.yaml").write_bytes(b"redirected external bytes")
    moved = project / "config-original"
    real_open = verifier.os.open
    fired = False

    def swap_after_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal fired
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == "config" and not fired:
            assert dir_fd is not None
            assert Path(os.readlink(f"/proc/self/fd/{dir_fd}")) == project
            fired = True
            config.rename(moved)
            config.symlink_to(external, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(verifier.os, "open", swap_after_open)
    identity: list[tuple[tuple[int, int], tuple[int, int, int]]] = []

    payload = _read_config_input(config, "authority.yaml", identity_out=identity)

    assert fired
    assert payload == expected
    current_inputs = {name: expected for name in verifier._CONFIG_INPUTS}
    identities = {name: identity[0] for name in verifier._CONFIG_INPUTS}
    assert _repository_commit(config, current_inputs, expected_identities=identities) == (
        None,
        False,
    )


def test_source_tamper_after_apply_is_drift(tmp_path: Path) -> None:
    desired, current, _, source = _fixture(tmp_path)
    (source / "SKILL.md").write_text(
        "---\nname: one\ndescription: changed\n---\n", encoding="utf-8"
    )

    result = verify_state(desired, current)

    assert result.result == "drift"
    assert [reason.code for reason in result.reasons] == ["source-content-hash-mismatch"]


def test_whole_cached_snapshot_tamper_is_checked_once_even_when_ungranted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    desired, current, _, source = _fixture(tmp_path)
    snapshot = source.parents[1]
    expected = hash_tree(snapshot)
    desired = DesiredState(desired.targets, (DesiredSource("source", snapshot, expected),))
    (snapshot / "ungranted.txt").write_text("tamper", encoding="utf-8")
    calls = 0
    real_hash = verifier.hash_tree

    def counted(path: Path) -> str:
        nonlocal calls
        if path == snapshot:
            calls += 1
        return real_hash(path)

    monkeypatch.setattr(verifier, "hash_tree", counted)
    result = verify_state(desired, current)

    assert result.result == "drift"
    assert "source-snapshot-hash-mismatch" in [reason.code for reason in result.reasons]
    assert calls == 1


def test_source_tamper_is_reported_even_when_target_scan_fails(tmp_path: Path) -> None:
    desired, current, target, source = _fixture(tmp_path)
    (source / "SKILL.md").write_text(
        "---\nname: renamed\ndescription: changed\n---\n", encoding="utf-8"
    )
    (target / "source" / "one").unlink()

    result = verify_state(desired, current)

    assert [reason.code for reason in result.reasons] == [
        "managed-link-missing",
        "runtime-name-mismatch",
        "source-content-hash-mismatch",
    ]
    assert result.operation_summary.verified_links == 0


def test_missing_broken_and_wrong_managed_links_are_ordinary_drift(tmp_path: Path) -> None:
    for mode in ("missing", "broken", "wrong"):
        case = tmp_path / mode
        desired, current, target, _ = _fixture(case)
        link = target / "source" / "one"
        link.unlink()
        if mode == "broken":
            link.symlink_to(case / "gone")
        elif mode == "wrong":
            wrong = case / "var" / "cache" / "sources" / "source" / "other" / "one"
            wrong.mkdir(parents=True)
            link.symlink_to(wrong)

        result = verify_state(desired, current)

        assert result.result == "drift"
        assert result.reasons[0].code == f"managed-link-{mode}"


def test_unexpected_manager_owned_entry_is_drift(tmp_path: Path) -> None:
    desired, current, target, source = _fixture(tmp_path)
    extra_source = source.parent / "extra"
    extra_source.mkdir()
    (extra_source / "SKILL.md").write_text(
        "---\nname: extra\ndescription: fixture\n---\n", encoding="utf-8"
    )
    extra = target / "source" / "extra"
    extra.symlink_to(extra_source)
    metadata_path = target / ".skill-delegator" / "managed.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["entries"].append(
        {
            "artifact_id": "source/extra",
            "source_path": str(extra_source),
            "content_sha256": hash_tree(extra_source),
        }
    )
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    result = verify_state(desired, current)

    assert result.result == "drift"
    assert [reason.code for reason in result.reasons] == ["unexpected-managed-entry"]


def test_hostile_metadata_and_source_symlink_escape_are_invalid(tmp_path: Path) -> None:
    desired, current, target, source = _fixture(tmp_path / "metadata")
    (target / ".skill-delegator" / "managed.json").write_text("{}", encoding="utf-8")
    result = verify_state(desired, current)
    assert result.result == "invalid"
    assert result.reasons[0].category == "invalid"
    assert len(result.reasons[0].detail) <= 300

    desired, current, _, source = _fixture(tmp_path / "source")
    (source / "escape").symlink_to(tmp_path / "outside")
    result = verify_state(desired, current)
    assert result.result == "invalid"
    assert result.reasons[0].code == "source-state-invalid"


def test_runtime_name_tamper_and_fresh_collision_are_detected(tmp_path: Path) -> None:
    desired, current, _, source = _fixture(tmp_path / "tamper", runtime_name="one")
    (source / "SKILL.md").write_text(
        "---\nname: renamed\ndescription: fixture\n---\n", encoding="utf-8"
    )
    new_digest = hash_tree(source)
    metadata_path = desired.targets[0].root / ".skill-delegator" / "managed.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["entries"][0]["content_sha256"] = new_digest
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    link = desired.targets[0].links[0]
    desired = DesiredState(
        (
            DesiredTarget(
                desired.targets[0].id,
                desired.targets[0].root,
                (
                    DesiredLink(
                        link.artifact_id,
                        link.runtime_name,
                        link.source_path,
                        link.target_path,
                        new_digest,
                        link.expected_source_path,
                    ),
                ),
            ),
        )
    )
    result = verify_state(desired, current)
    assert [reason.code for reason in result.reasons] == ["runtime-name-mismatch"]

    desired, current, target, source = _fixture(tmp_path / "collision", runtime_name="same")
    second_source = source.parent / "two"
    second_source.mkdir()
    (second_source / "SKILL.md").write_text(
        "---\nname: same\ndescription: fixture\n---\n", encoding="utf-8"
    )
    second_link = target / "source" / "two"
    second_link.symlink_to(second_source)
    metadata_path = target / ".skill-delegator" / "managed.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["entries"].append(
        {
            "artifact_id": "source/two",
            "source_path": str(second_source),
            "content_sha256": hash_tree(second_source),
        }
    )
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    first = desired.targets[0].links[0]
    desired = DesiredState(
        (
            DesiredTarget(
                "worker",
                target,
                (
                    first,
                    DesiredLink(
                        "source/two",
                        "other-in-lock",
                        PurePosixPath("skills/two"),
                        second_link,
                        hash_tree(second_source),
                        second_source,
                    ),
                ),
            ),
        )
    )

    result = verify_state(desired, current)

    assert "runtime-name-collision" in [reason.code for reason in result.reasons]


def test_verifier_does_not_trust_stale_current_target_objects(tmp_path: Path) -> None:
    desired, current, target, _ = _fixture(tmp_path)
    assert verify_state(desired, current).converged
    (target / "source" / "one").unlink()

    result = verify_state(desired, current)

    assert result.result == "drift"
    assert result.reasons[0].code == "managed-link-missing"
