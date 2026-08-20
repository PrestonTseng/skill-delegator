from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from skill_delegator import cli as cli_module
from skill_delegator import verifier as verifier_module
from tests.fixture_safety import run_cli


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
    assert run_cli(config, config.parent.parent, ["lock", "--config", str(config)]) == 0
    return config


def _use_per_target_delegations(config: Path, roots: dict[str, str]) -> None:
    (config / "delegations.yaml").unlink()
    delegations = config / "delegations"
    delegations.mkdir()
    for target_id, root in roots.items():
        document = {
            "schema_version": 1,
            "target": {
                "id": target_id,
                "root": root,
                "grants": ["example/one"],
            },
        }
        (delegations / f"{target_id}.yaml").write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )


def test_target_scoped_workflow_only_reads_and_mutates_selected_target(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()

    hostile = project / "targets" / "leo" / "example" / "one"
    hostile.parent.mkdir(parents=True)
    hostile.write_text("unmanaged", encoding="utf-8")

    assert (
        run_cli(
            config,
            config.parent.parent,
            ["plan", "--json", "--target", "niles", "--config", str(config)],
        )
        == 1
    )
    plan = json.loads(capsys.readouterr().out)
    assert {operation["target_id"] for operation in plan["operations"]} == {"niles"}

    assert (
        run_cli(
            config, config.parent.parent, ["apply", "--target", "niles", "--config", str(config)]
        )
        == 0
    )
    applied = capsys.readouterr()
    assert applied.out == "Applied 1 change to 1 target\n"
    assert hostile.read_text(encoding="utf-8") == "unmanaged"
    assert (project / "targets" / "niles" / "example" / "one").is_symlink()

    assert (
        run_cli(
            config,
            config.parent.parent,
            ["status", "--json", "--target", "niles", "--config", str(config)],
        )
        == 0
    )
    status = json.loads(capsys.readouterr().out)
    assert status["result"] == "converged"
    assert status["operation_summary"]["desired_targets"] == 1
    assert [item["target_id"] for item in status["target_fingerprints"]] == ["niles"]

    assert (
        run_cli(
            config, config.parent.parent, ["verify", "--target", "niles", "--config", str(config)]
        )
        == 0
    )
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
    assert run_cli(config, config.parent.parent, arguments) == 2
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

    assert (
        run_cli(
            config, config.parent.parent, ["apply", "--target", "niles", "--config", str(config)]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "target path collision" in captured.err
    assert not (project / "targets").exists()


def test_multi_file_equal_roots_allow_scoped_plan_and_scan_only_selected_target(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    _use_per_target_delegations(
        config,
        {
            "reviewer": "../targets/shared",
            "worker": "../targets/shared",
        },
    )
    scanned: list[str] = []
    real_scan_target = cli_module.scan_target

    def recording_scan(target):
        scanned.append(target.id)
        return real_scan_target(target)

    monkeypatch.setattr(cli_module, "scan_target", recording_scan)

    assert (
        run_cli(
            config,
            config.parent.parent,
            ["plan", "--json", "--target", "worker", "--config", str(config)],
        )
        == 1
    )
    plan = json.loads(capsys.readouterr().out)
    assert {operation["target_id"] for operation in plan["operations"]} == {"worker"}
    assert scanned == ["worker"]


@pytest.mark.parametrize("command", ["plan", "apply", "verify", "status"])
@pytest.mark.parametrize("overlap", ["equal", "parent-child"])
def test_unscoped_multi_file_overlapping_roots_fail_before_target_scan(
    command: str,
    overlap: str,
    tmp_path: Path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    second_root = "../targets/a" if overlap == "equal" else "../targets/a/child"
    _use_per_target_delegations(
        config,
        {
            "reviewer": "../targets/a",
            "worker": second_root,
        },
    )

    def forbidden_scan(*_args, **_kwargs):
        raise AssertionError("target scan must not run before overlap rejection")

    monkeypatch.setattr(cli_module, "scan_target", forbidden_scan)
    monkeypatch.setattr(verifier_module, "scan_target", forbidden_scan)

    assert run_cli(config, config.parent.parent, [command, "--config", str(config)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Target error: unscoped multi-file target roots overlap\n"
    assert len(captured.err) <= 80
    assert not (project / "targets").exists()


def test_unscoped_multi_file_distinct_roots_reach_both_targets(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    _use_per_target_delegations(
        config,
        {
            "reviewer": "../targets/reviewer",
            "worker": "../targets/worker",
        },
    )

    assert run_cli(config, config.parent.parent, ["plan", "--json", "--config", str(config)]) == 1
    plan = json.loads(capsys.readouterr().out)
    assert {operation["target_id"] for operation in plan["operations"]} == {
        "reviewer",
        "worker",
    }


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

    assert (
        run_cli(
            config, config.parent.parent, ["apply", "--target", selector, "--config", str(config)]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == message
    assert not (tmp_path / "project" / "targets").exists()
