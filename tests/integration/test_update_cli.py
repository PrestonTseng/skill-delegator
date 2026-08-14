from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from skill_delegator import cli
from skill_delegator.cli import main


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
            "authority": {
                "id": "test",
                "fail_closed": True,
                "fixture_policy": "none",
            },
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
    assert main(["lock", "--config", str(config)]) == 0
    return config, work, project / "target"


def test_check_is_byte_read_only_and_reports_stably(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config, work, target = fixture(tmp_path)
    capsys.readouterr()
    target.mkdir()
    (target / "sentinel").write_text("untouched", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in config.iterdir() if path.is_file()}
    inode = (config / "skill-lock.yaml").stat().st_ino
    write_skill(work, "two")
    git(work, "add", ".")
    git(work, "commit", "-qm", "two")
    git(work, "push", "-q", "origin", "main")

    first = main(["update", "--check", "--json", "--config", str(config)])
    first_output = capsys.readouterr()
    second = main(["update", "--check", "--json", "--config", str(config)])
    second_output = capsys.readouterr()

    assert first == second == 1
    assert first_output == second_output
    assert first_output.err == ""
    assert '"relation":"fast-forward"' in first_output.out
    assert {path.name: path.read_bytes() for path in config.iterdir() if path.is_file()} == before
    assert (config / "skill-lock.yaml").stat().st_ino == inode
    assert (target / "sentinel").read_text(encoding="utf-8") == "untouched"


def test_update_replaces_only_lock_after_validation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config, work, target = fixture(tmp_path)
    capsys.readouterr()
    before = {path.name: path.read_bytes() for path in config.iterdir() if path.is_file()}
    write_skill(work, "two")
    git(work, "add", ".")
    git(work, "commit", "-qm", "two")
    new_commit = git(work, "rev-parse", "HEAD")
    git(work, "push", "-q", "origin", "main")

    result = main(["update", "upstream", "--config", str(config)])
    captured = capsys.readouterr()

    assert result == 0
    assert captured.err == ""
    assert f"new: {new_commit}" in captured.out
    after = {path.name: path.read_bytes() for path in config.iterdir() if path.is_file()}
    assert {name: value for name, value in after.items() if name != "skill-lock.yaml"} == {
        name: value for name, value in before.items() if name != "skill-lock.yaml"
    }
    assert after["skill-lock.yaml"] != before["skill-lock.yaml"]
    assert not target.exists()


def test_option_conflicts_fail_closed_and_write_failure_preserves_original(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, work, _ = fixture(tmp_path)
    capsys.readouterr()
    assert main(["update", "upstream", "--all", "--config", str(config)]) == 2
    conflict = capsys.readouterr()
    assert conflict.out == ""
    assert "conflict" in conflict.err.lower()

    write_skill(work, "two")
    git(work, "add", ".")
    git(work, "commit", "-qm", "two")
    git(work, "push", "-q", "origin", "main")
    lock = config / "skill-lock.yaml"
    before = lock.read_bytes()
    inode = lock.stat().st_ino

    def fail_write(path: Path, candidate: object) -> None:
        raise OSError("injected candidate write failure")

    monkeypatch.setattr(cli, "write_lock_atomic", fail_write)
    assert main(["update", "upstream", "--config", str(config)]) == 3
    failed = capsys.readouterr()
    assert failed.out == ""
    assert "success" not in failed.err.lower()
    assert lock.read_bytes() == before
    assert lock.stat().st_ino == inode


def test_all_validates_every_candidate_before_single_lock_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, work, _ = fixture(tmp_path)
    capsys.readouterr()
    sources_path = config / "sources.yaml"
    sources = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
    second = dict(sources["sources"][0])
    second["id"] = "secondary"
    sources["sources"].append(second)
    sources_path.write_text(yaml.safe_dump(sources, sort_keys=False), encoding="utf-8")
    assert main(["lock", "--config", str(config)]) == 0
    capsys.readouterr()
    write_skill(work, "two")
    git(work, "add", ".")
    git(work, "commit", "-qm", "two")
    git(work, "push", "-q", "origin", "main")
    lock = config / "skill-lock.yaml"
    before = lock.read_bytes()
    original_prepare = cli.prepare_update

    def fail_second(source_id: str, authority: object, candidate: object):
        if source_id == "secondary":
            raise cli.SourceError("injected second candidate failure")
        return original_prepare(source_id, authority, candidate)

    monkeypatch.setattr(cli, "prepare_update", fail_second)
    assert main(["update", "--all", "--config", str(config)]) == 3
    failed = capsys.readouterr()
    assert failed.out == ""
    assert "injected second candidate failure" in failed.err
    assert lock.read_bytes() == before
