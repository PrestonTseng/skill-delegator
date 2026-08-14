from __future__ import annotations

import json
from pathlib import Path

import yaml

from skill_delegator.cli import main


def _write_config(project: Path) -> Path:
    config = project / "config"
    config.mkdir(parents=True)
    source = project / "source"
    for name in ("one", "two"):
        skill = source / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: fixture {name}\n---\nbody\n", encoding="utf-8"
        )
    documents = {
        "authority.yaml": {
            "schema_version": 1,
            "authority": {"id": "test", "fail_closed": True, "fixture_policy": "none"},
        },
        "sources.yaml": {
            "schema_version": 1,
            "sources": [
                {"id": "example", "type": "filesystem", "location": "../source", "skill_root": "."}
            ],
        },
        "pool.yaml": {"schema_version": 1, "skills": ["example/one", "example/two"]},
        "delegations.yaml": {
            "schema_version": 1,
            "targets": [
                {
                    "id": "worker",
                    "root": "../target",
                    "grants": ["example/one", "example/two"],
                }
            ],
        },
    }
    for filename, document in documents.items():
        (config / filename).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert main(["lock", "--config", str(config)]) == 0
    return config


def test_apply_cli_rebuilds_plan_applies_and_is_repeatable(tmp_path: Path, capsys) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()

    assert main(["apply", "--config", str(config)]) == 0
    first = capsys.readouterr()
    assert first.out == "Applied 2 changes to 1 target\n"
    assert first.err == ""
    target = tmp_path / "project" / "target"
    assert (target / "example" / "one").is_symlink()
    assert (target / "example" / "two").is_symlink()

    assert main(["apply", "--config", str(config)]) == 0
    repeat = capsys.readouterr()
    assert repeat.out == "Already converged\n"
    assert repeat.err == ""


def test_apply_cli_requires_yes_for_remove_and_preserves_unmanaged(tmp_path: Path, capsys) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    target = tmp_path / "project" / "target"
    sentinel = target / "mine.txt"
    sentinel.write_text("keep", encoding="utf-8")

    path = config / "delegations.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["targets"][0]["grants"] = ["example/one"]
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    assert main(["apply", "--config", str(config)]) == 4
    refused = capsys.readouterr()
    assert refused.out == ""
    assert refused.err == "Apply refused: plan contains REMOVE; pass --yes to confirm\n"
    assert (target / "example" / "two").is_symlink()

    assert main(["apply", "--yes", "--config", str(config)]) == 0
    applied = capsys.readouterr()
    assert applied.err == ""
    assert not (target / "example" / "two").exists()
    assert sentinel.read_text(encoding="utf-8") == "keep"
    metadata = json.loads((target / ".skill-delegator" / "managed.json").read_text())
    assert [entry["artifact_id"] for entry in metadata["entries"]] == ["example/one"]


def test_apply_cli_rejects_blocked_target_without_traceback(tmp_path: Path, capsys) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()
    occupied = tmp_path / "project" / "target" / "example" / "one"
    occupied.parent.mkdir(parents=True)
    occupied.write_text("unmanaged", encoding="utf-8")

    assert main(["apply", "--config", str(config)]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("Apply blocked: target worker desired path")
    assert "Traceback" not in captured.err
    assert occupied.read_text(encoding="utf-8") == "unmanaged"
