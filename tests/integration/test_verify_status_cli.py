from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import yaml

from skill_delegator.cli import main


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_config(project: Path, *, initialize_git: bool = False) -> Path:
    config = project / "config"
    config.mkdir(parents=True)
    source = project / "source" / "skills" / "one"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text(
        "---\nname: one\ndescription: fixture\n---\nbody\n", encoding="utf-8"
    )
    documents = {
        "authority.yaml": {
            "schema_version": 1,
            "authority": {"id": "test", "fail_closed": True, "fixture_policy": "none"},
        },
        "sources.yaml": {
            "schema_version": 1,
            "sources": [
                {
                    "id": "example",
                    "type": "filesystem",
                    "location": "../source",
                    "skill_root": "skills",
                }
            ],
        },
        "pool.yaml": {"schema_version": 1, "skills": ["example/one"]},
        "delegations.yaml": {
            "schema_version": 1,
            "targets": [{"id": "worker", "root": "../target", "grants": ["example/one"]}],
        },
    }
    for filename, document in documents.items():
        (config / filename).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    if initialize_git:
        _git(project, "init", "-q")
        _git(project, "config", "user.email", "test@example.invalid")
        _git(project, "config", "user.name", "Test")
        _git(project, "add", ".")
        _git(project, "commit", "-qm", "fixture")
    assert main(["lock", "--config", str(config)]) == 0
    if initialize_git:
        _git(project, "add", "config/skill-lock.yaml")
        _git(project, "commit", "-qm", "lock")
    return config


def _snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    if not root.exists():
        return ()
    records = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            records.append((relative, "link", os.readlink(path)))
        elif path.is_file():
            records.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        else:
            records.append((relative, "dir", ""))
    return tuple(records)


def test_verify_writes_deterministic_receipt_and_status_is_strictly_read_only(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    target = project / "target"
    target_before = _snapshot(target)
    config_before = _snapshot(config)

    assert main(["status", "--config", str(config)]) == 0
    human = capsys.readouterr()
    assert human.out == "converged: 1/1 links verified across 1 target\n"
    assert human.err == ""
    assert not (project / "var" / "receipts").exists()
    assert _snapshot(target) == target_before
    assert _snapshot(config) == config_before

    assert main(["status", "--json", "--config", str(config)]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["result"] == "converged"
    assert document["operation_summary"]["verified_links"] == 1
    assert not (project / "var" / "receipts").exists()

    assert main(["verify", "--config", str(config)]) == 0
    first = capsys.readouterr()
    assert first.err == ""
    receipt_path = Path(first.out.strip().split("receipt: ", 1)[1])
    first_bytes = receipt_path.read_bytes()
    assert receipt_path.parent == project / "var" / "receipts"
    assert _snapshot(target) == target_before
    assert _snapshot(config) == config_before

    assert main(["verify", "--config", str(config)]) == 0
    second = capsys.readouterr()
    assert Path(second.out.strip().split("receipt: ", 1)[1]) == receipt_path
    assert receipt_path.read_bytes() == first_bytes
    assert len(list(receipt_path.parent.glob("*.json"))) == 1


def test_verify_distinguishes_drift_from_hostile_target_without_traceback(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    link = project / "target" / "example" / "one"
    link.unlink()

    assert main(["verify", "--config", str(config)]) == 1
    drift = capsys.readouterr()
    assert "drift" in drift.out
    assert "managed-link-missing" in drift.out
    assert "Traceback" not in drift.err

    metadata = project / "target" / ".skill-delegator" / "managed.json"
    metadata.write_text("{}", encoding="utf-8")
    assert main(["status", "--config", str(config)]) == 3
    hostile = capsys.readouterr()
    assert hostile.out.startswith("invalid:")
    assert "Traceback" not in hostile.err


def test_receipt_hashes_exact_config_and_lock_bytes_and_captures_detached_commit(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "repository"
    config = _write_config(project, initialize_git=True)
    expected_commit = _git(project, "rev-parse", "HEAD")
    _git(project, "checkout", "--detach", "-q", expected_commit)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()

    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])
    document = json.loads(receipt.read_text())

    assert document["repository"] == {"available": True, "commit": expected_commit}
    assert {item["name"]: item["sha256"] for item in document["config_hashes"]} == {
        name: hashlib.sha256((config / name).read_bytes()).hexdigest()
        for name in (
            "authority.yaml",
            "delegations.yaml",
            "pool.yaml",
            "skill-lock.yaml",
            "sources.yaml",
        )
    }


def test_non_git_repository_records_explicit_unavailable_commit(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])

    assert json.loads(receipt.read_text())["repository"] == {
        "available": False,
        "commit": None,
    }


def test_untracked_nested_config_does_not_capture_unrelated_ancestor_commit(
    tmp_path: Path, capsys
) -> None:
    outer = tmp_path / "outer"
    outer.mkdir()
    _git(outer, "init", "-q")
    _git(outer, "config", "user.email", "test@example.invalid")
    _git(outer, "config", "user.name", "Test")
    (outer / "owned.txt").write_text("outer repository\n", encoding="utf-8")
    _git(outer, "add", "owned.txt")
    _git(outer, "commit", "-qm", "outer")
    config = _write_config(outer / "untracked-project")
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()

    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])

    assert json.loads(receipt.read_text())["repository"] == {
        "available": False,
        "commit": None,
    }
