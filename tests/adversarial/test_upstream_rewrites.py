from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from skill_delegator import cli
from tests.fixture_safety import run_cli


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def write_skill(root: Path, body: str) -> None:
    skill = root / "skills" / "one"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: one\ndescription: fixture\n---\n{body}\n", encoding="utf-8"
    )


def fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    project = tmp_path / "project"
    config = project / "config"
    config.mkdir(parents=True)
    work = tmp_path / "work"
    bare = tmp_path / "remote.git"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "user.email", "test@example.invalid")
    git(work, "config", "user.name", "Test")
    write_skill(work, "one")
    git(work, "add", ".")
    git(work, "commit", "-qm", "one")
    git(tmp_path, "init", "--bare", "-q", str(bare))
    git(work, "remote", "add", "origin", str(bare))
    git(work, "push", "-q", "-u", "origin", "main")
    documents = {
        "authority.yaml": {
            "schema_version": 1,
            "authority": {"id": "test", "fail_closed": True, "fixture_policy": "none"},
        },
        "sources.yaml": {
            "schema_version": 1,
            "sources": [
                {
                    "id": "upstream",
                    "type": "git",
                    "location": str(bare),
                    "track": "main",
                    "skill_root": "skills",
                }
            ],
        },
        "pool.yaml": {"schema_version": 1, "skills": ["upstream/one"]},
        "delegations.yaml": {
            "schema_version": 1,
            "targets": [{"id": "worker", "root": "../target", "grants": ["upstream/one"]}],
        },
    }
    for name, document in documents.items():
        (config / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert run_cli(config, config.parent.parent, ["lock", "--config", str(config)]) == 0
    return config, work, project / "target"


def test_check_and_update_do_not_apply_stage_or_change_repository_history(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, work, target = fixture(tmp_path)
    project = config.parent
    capsys.readouterr()
    git(project, "init", "-q", "-b", "main")
    git(project, "config", "user.email", "test@example.invalid")
    git(project, "config", "user.name", "Test")
    git(project, "add", ".")
    git(project, "commit", "-qm", "authority")
    original_head = git(project, "rev-parse", "HEAD")
    original_index = git(project, "write-tree")
    write_skill(work, "two")
    git(work, "add", ".")
    git(work, "commit", "-qm", "two")
    git(work, "push", "-q", "origin", "main")

    def forbidden_apply(*args: object, **kwargs: object) -> None:
        raise AssertionError("update must not apply")

    monkeypatch.setattr(cli, "apply_plan", forbidden_apply)
    assert (
        run_cli(config, config.parent.parent, ["update", "--check", "--config", str(config)]) == 1
    )
    capsys.readouterr()
    assert git(project, "status", "--porcelain") == ""
    assert git(project, "rev-parse", "HEAD") == original_head
    assert git(project, "write-tree") == original_index
    assert not target.exists()

    assert (
        run_cli(config, config.parent.parent, ["update", "upstream", "--config", str(config)]) == 0
    )
    capsys.readouterr()
    assert git(project, "diff", "--name-only") == "config/skill-lock.yaml"
    assert git(project, "diff", "--cached", "--name-only") == ""
    assert git(project, "rev-parse", "HEAD") == original_head
    assert git(project, "write-tree") == original_index
    assert not target.exists()
