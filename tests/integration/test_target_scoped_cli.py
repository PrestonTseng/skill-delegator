from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from skill_delegator.cli import main


def _write_config(project: Path) -> Path:
    config = project / "config"
    config.mkdir(parents=True)
    skill = project / "source" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: one\ndescription: fixture one\n---\nbody\n", encoding="utf-8"
    )
    documents = {
        "authority.yaml": {
            "schema_version": 1,
            "authority": {"id": "preston", "fail_closed": True, "fixture_policy": "none"},
        },
        "sources.yaml": {
            "schema_version": 1,
            "sources": [
                {
                    "id": "example",
                    "type": "filesystem",
                    "location": "../source",
                    "skill_root": ".",
                }
            ],
        },
        "pool.yaml": {"schema_version": 1, "skills": ["example/one"]},
        "delegations.yaml": {
            "schema_version": 1,
            "targets": [
                {"id": "leo", "root": "../targets/leo", "grants": ["example/one"]},
                {"id": "niles", "root": "../targets/niles", "grants": ["example/one"]},
            ],
        },
    }
    for filename, document in documents.items():
        (config / filename).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert main(["lock", "--config", str(config)]) == 0
    return config


def test_target_scoped_workflow_only_reads_and_mutates_selected_target(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()

    hostile = project / "targets" / "leo" / "example" / "one"
    hostile.parent.mkdir(parents=True)
    hostile.write_text("unmanaged", encoding="utf-8")

    assert main(["plan", "--json", "--target", "niles", "--config", str(config)]) == 1
    plan = json.loads(capsys.readouterr().out)
    assert {operation["target_id"] for operation in plan["operations"]} == {"niles"}

    assert main(["apply", "--target", "niles", "--config", str(config)]) == 0
    applied = capsys.readouterr()
    assert applied.out == "Applied 1 change to 1 target\n"
    assert hostile.read_text(encoding="utf-8") == "unmanaged"
    assert (project / "targets" / "niles" / "example" / "one").is_symlink()

    assert main(["status", "--json", "--target", "niles", "--config", str(config)]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["result"] == "converged"
    assert status["operation_summary"]["desired_targets"] == 1
    assert [item["target_id"] for item in status["target_fingerprints"]] == ["niles"]

    assert main(["verify", "--target", "niles", "--config", str(config)]) == 0
    verified = capsys.readouterr()
    assert "converged: 1/1 links verified across 1 target" in verified.out
    assert hostile.read_text(encoding="utf-8") == "unmanaged"


@pytest.mark.parametrize("command", ["plan", "apply", "verify", "status"])
def test_target_scoped_commands_reject_unknown_target_without_mutation(
    command: str, tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    arguments = [command, "--target", "missing", "--config", str(config)]
    assert main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Target error: unknown target selector\n"
    assert not (project / "targets").exists()


def test_target_scope_keeps_whole_authority_collision_validation(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    delegations = yaml.safe_load((config / "delegations.yaml").read_text(encoding="utf-8"))
    for target in delegations["targets"]:
        target["root"] = "../targets/shared"
    (config / "delegations.yaml").write_text(
        yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8"
    )

    assert main(["apply", "--target", "niles", "--config", str(config)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "target path collision" in captured.err
    assert not (project / "targets").exists()


@pytest.mark.parametrize(
    ("selector", "message"),
    [
        ("bad\nspoof", "Target error: invalid target selector\n"),
        ("a" * 1000, "Target error: unknown target selector\n"),
    ],
)
def test_invalid_target_selector_has_bounded_single_line_error(
    selector: str, message: str, tmp_path: Path, capsys
) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()

    assert main(["apply", "--target", selector, "--config", str(config)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == message
    assert not (tmp_path / "project" / "targets").exists()
