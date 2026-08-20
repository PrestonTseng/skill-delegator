from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixture_safety import assert_before_mutation, assert_mutation_fixture_confined

TARGET_IDS = ("alpha", "beta", "gamma")


def _run(project: Path, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    assert_before_mutation(project, project.parent, arguments[0])
    result = subprocess.run(
        [sys.executable, "-m", "skill_delegator.cli", *arguments],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected, (arguments, result.stdout, result.stderr)
    assert "Traceback" not in result.stderr
    return result


def _write_yaml(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _project(tmp_path: Path, roots: dict[str, str] | None = None) -> Path:
    project = tmp_path / "project"
    config = project / "config"
    skill = project / "source" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: one\ndescription: generic fixture\n---\nbody\n", encoding="utf-8"
    )
    _write_yaml(
        config / "authority.yaml",
        {
            "schema_version": 1,
            "authority": {"id": "generic", "fail_closed": True, "fixture_policy": "none"},
        },
    )
    _write_yaml(
        config / "sources.yaml",
        {
            "schema_version": 1,
            "sources": [
                {
                    "id": "source",
                    "type": "filesystem",
                    "location": "../source",
                    "skill_root": ".",
                }
            ],
        },
    )
    _write_yaml(config / "pool.yaml", {"schema_version": 1, "skills": ["source/one"]})
    configured_roots = roots or {target_id: f"../targets/{target_id}" for target_id in TARGET_IDS}
    for target_id, root in configured_roots.items():
        _write_yaml(
            config / "delegations" / f"{target_id}.yaml",
            {
                "schema_version": 1,
                "target": {
                    "id": target_id,
                    "root": root,
                    "grants": ["source/one"],
                },
            },
        )
    assert_mutation_fixture_confined(project, tmp_path)
    _run(project, "lock")
    return project


def _snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    if not os.path.lexists(root):
        return ((".", "absent", ""),)
    entries = [root, *sorted(root.rglob("*"), key=lambda path: os.fsencode(path.as_posix()))]
    snapshot: list[tuple[str, str, str]] = []
    for path in entries:
        relative = "." if path == root else path.relative_to(root).as_posix()
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            snapshot.append((relative, "link", os.readlink(path)))
        elif stat.S_ISREG(metadata.st_mode):
            snapshot.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        elif stat.S_ISDIR(metadata.st_mode):
            snapshot.append((relative, "directory", ""))
        else:
            snapshot.append((relative, f"type:{stat.S_IFMT(metadata.st_mode)}", ""))
    return tuple(snapshot)


def _receipt_path(output: str) -> Path:
    return Path(output.strip().split("receipt: ", 1)[1])


def test_generic_multi_file_scoped_apply_preserves_every_unselected_root(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    resolved = json.loads(_run(project, "resolve", "--json").stdout)
    target_ids = tuple(target["id"] for target in resolved["targets"])
    assert set(target_ids) == set(TARGET_IDS)
    roots = {target["id"]: Path(target["root"]) for target in resolved["targets"]}

    for selected_id in target_ids:
        unselected_before = {
            target_id: _snapshot(root)
            for target_id, root in roots.items()
            if target_id != selected_id
        }

        assert _run(project, "apply", "--target", selected_id).stdout == (
            "Applied 1 change to 1 target\n"
        )
        assert {
            target_id: _snapshot(root)
            for target_id, root in roots.items()
            if target_id != selected_id
        } == unselected_before

        verification = _run(project, "verify", "--target", selected_id)
        assert verification.stdout.startswith("converged: 1/1 links verified across 1 target\n")
        receipt_path = _receipt_path(verification.stdout)
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        assert receipt_path.name == f"{hashlib.sha256(receipt_bytes).hexdigest()}.json"
        assert receipt["operation_summary"]["desired_targets"] == 1
        assert receipt["operation_summary"]["desired_links"] == 1
        assert [item["target_id"] for item in receipt["target_fingerprints"]] == [selected_id]

        status = json.loads(_run(project, "status", "--json", "--target", selected_id).stdout)
        assert status["result"] == "converged"
        assert status["operation_summary"]["desired_targets"] == 1
        assert status["operation_summary"]["verified_links"] == 1
        assert [item["target_id"] for item in status["target_fingerprints"]] == [selected_id]

        assert _run(project, "apply", "--target", selected_id).stdout == "Already converged\n"
        second_receipt = _receipt_path(_run(project, "verify", "--target", selected_id).stdout)
        assert second_receipt == receipt_path
        assert second_receipt.read_bytes() == receipt_bytes


def test_generic_multi_file_distinct_roots_apply_unscoped(tmp_path: Path) -> None:
    project = _project(tmp_path)

    assert _run(project, "apply").stdout == "Applied 3 changes to 3 targets\n"
    verification = _run(project, "verify")
    assert verification.stdout.startswith("converged: 3/3 links verified across 3 targets\n")
    receipt = json.loads(_receipt_path(verification.stdout).read_bytes())
    assert receipt["operation_summary"]["desired_targets"] == 3
    assert {item["target_id"] for item in receipt["target_fingerprints"]} == set(TARGET_IDS)


@pytest.mark.parametrize(
    "roots",
    [
        {"alpha": "../targets/shared", "beta": "../targets/shared"},
        {"alpha": "../targets/parent", "beta": "../targets/parent/child"},
    ],
    ids=("equal", "parent-child"),
)
def test_generic_multi_file_overlapping_roots_fail_unscoped_before_mutation(
    tmp_path: Path, roots: dict[str, str]
) -> None:
    project = _project(tmp_path, roots)
    targets = project / "targets"
    before = _snapshot(targets)

    result = _run(project, "apply", expected=2)

    assert result.stdout == ""
    assert result.stderr == "Target error: unscoped multi-file target roots overlap\n"
    assert _snapshot(targets) == before
