from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from skill_delegator import source_store
from skill_delegator.cli import main
from tests.fixture_safety import assert_before_mutation, copy_mutation_config

REPOSITORY_ROOT = Path(__file__).parents[2]


def run_lock(config_dir: Path) -> subprocess.CompletedProcess[str]:
    assert_before_mutation(config_dir.parent, config_dir.parent.parent, "lock")
    return subprocess.run(
        [sys.executable, "-m", "skill_delegator.cli", "lock", "--config", str(config_dir)],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def run_validate(config_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skill_delegator.cli", "validate", "--config", str(config_dir)],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_lock_cli_is_byte_stable_and_never_touches_target_roots(tmp_path: Path) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    copy_mutation_config(REPOSITORY_ROOT, config_dir.parent)
    source = project / "source"
    source.mkdir(parents=True)
    skill = source / "hello"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: hello\ndescription: Hello fixture\n---\nbody\n", encoding="utf-8"
    )

    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    sources["sources"][0]["location"] = "../source"
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )
    targets = yaml.safe_load((config_dir / "delegations.yaml").read_text(encoding="utf-8"))
    target_roots: list[Path] = []
    for index, target in enumerate(targets["targets"]):
        target["root"] = f"../var/example-targets/target-{index}"
        root = project / "var" / "example-targets" / f"target-{index}"
        root.mkdir(parents=True)
        (root / "sentinel").write_text("untouched", encoding="utf-8")
        target_roots.append(root)
    (config_dir / "delegations.yaml").write_text(
        yaml.safe_dump(targets, sort_keys=False), encoding="utf-8"
    )
    (config_dir / "skill-lock.yaml").unlink()
    assert not (config_dir / "skill-lock.yaml").exists()

    before_targets = {
        root: tuple(sorted(path.relative_to(root) for path in root.rglob("*")))
        for root in target_roots
    }
    first = run_lock(config_dir)
    first_bytes = (config_dir / "skill-lock.yaml").read_bytes()
    second = run_lock(config_dir)

    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout == "Locked 1 skill from 1 source\n"
    assert first.stderr == second.stderr == ""
    assert (config_dir / "skill-lock.yaml").read_bytes() == first_bytes
    after_targets = {
        root: tuple(sorted(path.relative_to(root) for path in root.rglob("*")))
        for root in target_roots
    }
    assert after_targets == before_targets
    assert all(
        (root / "sentinel").read_text(encoding="utf-8") == "untouched" for root in target_roots
    )


def test_hidden_configured_skill_root_lock_validates_loads_and_resolves(tmp_path: Path) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    copy_mutation_config(REPOSITORY_ROOT, config_dir.parent)
    source = project / "source"
    skill = source / ".claude" / "skills" / "banner-design"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: banner-design\ndescription: Banner design fixture\n---\nbody\n",
        encoding="utf-8",
    )

    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    sources["sources"][0].update(
        {"id": "source", "location": "../source", "skill_root": ".claude/skills"}
    )
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )
    pool = {"schema_version": 1, "skills": ["source/banner-design"]}
    (config_dir / "pool.yaml").write_text(yaml.safe_dump(pool, sort_keys=False), encoding="utf-8")
    delegations = yaml.safe_load((config_dir / "delegations.yaml").read_text(encoding="utf-8"))
    for target in delegations["targets"]:
        target["grants"] = ["source/banner-design"]
    (config_dir / "delegations.yaml").write_text(
        yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8"
    )

    locked = run_lock(config_dir)
    document = yaml.safe_load((config_dir / "skill-lock.yaml").read_text(encoding="utf-8"))
    validated = run_validate(config_dir)
    resolved = subprocess.run(
        [
            sys.executable,
            "-m",
            "skill_delegator.cli",
            "resolve",
            "--json",
            "--config",
            str(config_dir),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert locked.returncode == 0, locked.stderr
    locked_skill = document["sources"][0]["skills"][0]
    assert locked_skill["canonical_id"] == "source/banner-design"
    assert locked_skill["path"] == ".claude/skills/banner-design"
    assert validated.returncode == 0, validated.stderr
    assert resolved.returncode == 0, resolved.stderr
    resolved_document = json.loads(resolved.stdout)
    links = [link for target in resolved_document["targets"] for link in target["links"]]
    assert {link["artifact_id"] for link in links} == {"source/banner-design"}
    assert {link["source_path"] for link in links} == {".claude/skills/banner-design"}


def test_validate_cli_still_requires_missing_lock_with_precise_exit_2(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    copy_mutation_config(REPOSITORY_ROOT, config_dir.parent)
    (config_dir / "skill-lock.yaml").unlink()

    result = run_validate(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("Configuration error: skill-lock.yaml: cannot read file:")
    assert "Traceback" not in result.stderr


def test_lock_cli_rejects_unrelated_escaping_symlink_without_publishing_cache(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    copy_mutation_config(REPOSITORY_ROOT, config_dir.parent)
    source = project / "source"
    skill = source / "hello"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: hello\ndescription: Hello fixture\n---\nbody\n", encoding="utf-8"
    )
    outside = project / "outside"
    outside.write_text("external", encoding="utf-8")
    (source / "unrelated-link").symlink_to(outside)
    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    sources["sources"][0]["location"] = "../source"
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )

    result = run_lock(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Lock error: symlink escape from source root:" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (project / "var" / "cache" / "sources").exists()


def test_lock_cli_wraps_posix_competing_directory_race_as_precise_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    copy_mutation_config(REPOSITORY_ROOT, config_dir.parent)
    source = project / "source"
    skill = source / "hello"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: hello\ndescription: Hello fixture\n---\nbody\n", encoding="utf-8"
    )
    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    sources["sources"][0]["location"] = "../source"
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )

    def compete(
        staging: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        assert src_dir_fd is None
        assert dst_dir_fd is not None
        cache_destination = (
            project / "var" / "cache" / "sources" / "example" / os.fsdecode(destination)
        )
        cache_destination.mkdir()
        (cache_destination / "corrupt").write_text("wrong", encoding="utf-8")
        raise OSError(errno.ENOTEMPTY, "competing directory")

    monkeypatch.setattr(source_store.os, "rename", compete)

    assert_before_mutation(project, tmp_path, "lock")
    result = main(["lock", "--config", str(config_dir)])
    captured = capsys.readouterr()

    assert result == 2
    assert captured.out == ""
    assert captured.err.startswith(
        "Lock error: content-addressed cache race produced corrupt entry:"
    )
    assert "Traceback" not in captured.err
    assert not tuple((project / "var" / "cache" / "sources" / "example").glob(".snapshot-*"))


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte-oriented filenames")
def test_lock_cli_hashes_unrelated_non_utf8_entries_without_traceback(tmp_path: Path) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    copy_mutation_config(REPOSITORY_ROOT, config_dir.parent)
    source = project / "source"
    skill = source / "hello"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: hello\ndescription: Hello fixture\n---\nbody\n", encoding="utf-8"
    )
    source_bytes = os.fsencode(source)
    unrelated = os.path.join(source_bytes, b"unrelated-\xff")
    with open(unrelated, "wb") as stream:
        stream.write(b"payload")
    os.symlink(b"unrelated-\xff", os.path.join(source_bytes, b"link-\xfe"))
    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    sources["sources"][0]["location"] = "../source"
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )

    first = run_lock(config_dir)
    first_bytes = (config_dir / "skill-lock.yaml").read_bytes() if first.returncode == 0 else b""
    second = run_lock(config_dir)

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert "Traceback" not in first.stderr + second.stderr
    assert (config_dir / "skill-lock.yaml").read_bytes() == first_bytes


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte-oriented filenames")
def test_lock_cli_rejects_non_utf8_skill_id_with_precise_exit_2(tmp_path: Path) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    copy_mutation_config(REPOSITORY_ROOT, config_dir.parent)
    source = project / "source"
    source.mkdir(parents=True)
    skill = os.path.join(os.fsencode(source), b"skill-\xff")
    os.mkdir(skill)
    with open(os.path.join(skill, b"SKILL.md"), "wb") as stream:
        stream.write(b"---\nname: runtime\ndescription: Test skill\n---\n")
    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    sources["sources"][0]["location"] = "../source"
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )

    result = run_lock(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "Lock error: skill path cannot form a UTF-8 canonical id:" in result.stderr
    assert "Traceback" not in result.stderr
