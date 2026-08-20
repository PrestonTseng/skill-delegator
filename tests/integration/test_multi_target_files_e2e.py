from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

from skill_delegator import cli
from tests.fixture_safety import assert_mutation_fixture_confined, run_cli

TARGET_IDS = ("alpha", "beta", "gamma")


def _run(project: Path, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = run_cli(
        project / "config",
        project.parent,
        [*arguments, "--config", str(project / "config")],
        cwd=project,
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


def _expected_config_hashes(project: Path) -> list[dict[str, str]]:
    names = [
        "authority.yaml",
        *(f"delegations/{target_id}.yaml" for target_id in TARGET_IDS),
        "pool.yaml",
        "skill-lock.yaml",
        "sources.yaml",
    ]
    return [
        {
            "name": name,
            "sha256": hashlib.sha256((project / "config" / name).read_bytes()).hexdigest(),
        }
        for name in names
    ]


def test_generic_multi_file_scoped_apply_preserves_every_unselected_root(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    resolved = json.loads(_run(project, "resolve", "--json").stdout)
    target_ids = tuple(target["id"] for target in resolved["targets"])
    assert set(target_ids) == set(TARGET_IDS)
    roots = {target["id"]: Path(target["root"]) for target in resolved["targets"]}
    link_counts = {target["id"]: len(target["links"]) for target in resolved["targets"]}

    for selected_id in target_ids:
        unselected_before = {
            target_id: _snapshot(root)
            for target_id, root in roots.items()
            if target_id != selected_id
        }

        expected_links = link_counts[selected_id]
        change_word = "change" if expected_links == 1 else "changes"
        assert _run(project, "apply", "--target", selected_id).stdout == (
            f"Applied {expected_links} {change_word} to 1 target\n"
        )
        assert {
            target_id: _snapshot(root)
            for target_id, root in roots.items()
            if target_id != selected_id
        } == unselected_before

        verification = _run(project, "verify", "--target", selected_id)
        assert verification.stdout.startswith(
            f"converged: {expected_links}/{expected_links} links verified across 1 target\n"
        )
        receipt_path = _receipt_path(verification.stdout)
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        assert receipt_path.name == f"{hashlib.sha256(receipt_bytes).hexdigest()}.json"
        assert receipt["operation_summary"]["desired_targets"] == 1
        assert receipt["operation_summary"]["desired_links"] == expected_links
        assert [item["target_id"] for item in receipt["target_fingerprints"]] == [selected_id]
        assert receipt["config_hashes"] == _expected_config_hashes(project)

        status = json.loads(_run(project, "status", "--json", "--target", selected_id).stdout)
        assert status["result"] == "converged"
        assert status["operation_summary"]["desired_targets"] == 1
        assert status["operation_summary"]["verified_links"] == expected_links
        assert [item["target_id"] for item in status["target_fingerprints"]] == [selected_id]
        assert status["config_hashes"] == _expected_config_hashes(project)

        assert _run(project, "apply", "--target", selected_id).stdout == "Already converged\n"
        second_receipt = _receipt_path(_run(project, "verify", "--target", selected_id).stdout)
        assert second_receipt == receipt_path
        assert second_receipt.read_bytes() == receipt_bytes


def test_generic_multi_file_distinct_roots_apply_unscoped(tmp_path: Path) -> None:
    project = _project(tmp_path)
    resolved = json.loads(_run(project, "resolve", "--json").stdout)
    target_count = len(resolved["targets"])
    link_count = sum(len(target["links"]) for target in resolved["targets"])
    target_word = "target" if target_count == 1 else "targets"
    change_word = "change" if link_count == 1 else "changes"

    assert _run(project, "apply").stdout == (
        f"Applied {link_count} {change_word} to {target_count} {target_word}\n"
    )
    verification = _run(project, "verify")
    assert verification.stdout.startswith(
        f"converged: {link_count}/{link_count} links verified across {target_count} {target_word}\n"
    )
    receipt = json.loads(_receipt_path(verification.stdout).read_bytes())
    assert receipt["operation_summary"]["desired_targets"] == target_count
    assert receipt["operation_summary"]["desired_links"] == link_count
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
    tmp_path: Path,
    roots: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _project(tmp_path, roots)
    targets = project / "targets"
    before = _snapshot(targets)

    scan_calls = 0

    def scan_sentinel(*_arguments: object, **_keywords: object) -> object:
        nonlocal scan_calls
        scan_calls += 1
        raise AssertionError("scan_target must not run for overlapping roots")

    monkeypatch.setattr(cli, "scan_target", scan_sentinel)
    exit_code = run_cli(
        project / "config", tmp_path, ["apply", "--config", str(project / "config")]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "Target error: unscoped multi-file target roots overlap\n"
    assert scan_calls == 0
    assert _snapshot(targets) == before
