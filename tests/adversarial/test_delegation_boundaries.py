from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest
import yaml

from skill_delegator.models import (
    AuthorityConfig,
    LockedSkill,
    LockedSource,
    PoolSpec,
    SkillLock,
    SourceSpec,
    TargetSpec,
)
from skill_delegator.resolver import ResolutionError, resolve_desired_state

REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "config"
_SHA = "a" * 64


def authority(tmp_path: Path, pool: tuple[str, ...], grants: tuple[str, ...]) -> AuthorityConfig:
    return AuthorityConfig(
        "test",
        True,
        "none",
        (
            SourceSpec("one", "filesystem", tmp_path / "one", PurePosixPath(".")),
            SourceSpec("two", "filesystem", tmp_path / "two", PurePosixPath(".")),
        ),
        tuple(PoolSpec(item) for item in pool),
        (TargetSpec("worker", tmp_path / "target", grants),),
    )


def locked(source_id: str, artifact_id: str, name: str, path: str) -> LockedSource:
    return LockedSource(
        source_id,
        "filesystem",
        None,
        "f" * 64,
        (LockedSkill(artifact_id, name, PurePosixPath(path), _SHA),),
    )


def test_rejects_grant_absent_from_pool(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/allowed",), ("one/forbidden",))
    lock = SkillLock(1, (locked("one", "one/forbidden", "forbidden", "forbidden"),))
    with pytest.raises(ResolutionError, match="outside pool.*one/forbidden"):
        resolve_desired_state(config, lock)


def test_rejects_grant_absent_from_lock(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/missing",), ("one/missing",))
    with pytest.raises(ResolutionError, match="absent from lock.*one/missing"):
        resolve_desired_state(config, SkillLock(1, ()))


def test_rejects_duplicate_grants_even_when_models_bypass_yaml_schema(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/tool",), ("one/tool", "one/tool"))
    lock = SkillLock(1, (locked("one", "one/tool", "tool", "tool"),))
    with pytest.raises(ResolutionError, match="duplicate grant.*one/tool"):
        resolve_desired_state(config, lock)


def test_rejects_duplicate_runtime_name_per_target_across_sources(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/a", "two/b"), ("one/a", "two/b"))
    lock = SkillLock(
        1,
        (locked("one", "one/a", "shared", "skills/a"), locked("two", "two/b", "shared", "b")),
    )
    with pytest.raises(ResolutionError, match="duplicate runtime name.*shared"):
        resolve_desired_state(config, lock)


def test_rejects_normalized_target_escape(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/../../escape",), ("one/../../escape",))
    lock = SkillLock(1, (locked("one", "one/../../escape", "escape", "escape"),))
    with pytest.raises(ResolutionError, match="outside target root"):
        resolve_desired_state(config, lock)


def test_rejects_normalized_target_path_collision(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/a/../same", "one/same"), ("one/a/../same", "one/same"))
    lock = SkillLock(
        1,
        (
            replace(
                locked("one", "one/a/../same", "first", "first"),
                skills=(
                    LockedSkill("one/a/../same", "first", PurePosixPath("first"), _SHA),
                    LockedSkill("one/same", "second", PurePosixPath("second"), _SHA),
                ),
            ),
        ),
    )
    with pytest.raises(ResolutionError, match="target path collision"):
        resolve_desired_state(config, lock)


def snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    values: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*")):
        kind = "link" if path.is_symlink() else "dir" if path.is_dir() else "file"
        payload = (
            os.readlink(path) if path.is_symlink() else path.read_text() if path.is_file() else ""
        )
        values.append((path.relative_to(root).as_posix(), kind, payload))
    return tuple(values)


def test_resolve_cli_json_is_repeatable_and_does_not_touch_target_roots(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)
    document = yaml.safe_load((config_dir / "delegations.yaml").read_text())
    target_roots: list[Path] = []
    for index, target in enumerate(document["targets"]):
        target["root"] = f"../var/example-targets/{index}"
        root = tmp_path / "var" / "example-targets" / str(index)
        root.mkdir(parents=True)
        (root / "sentinel").write_text(f"sentinel-{index}")
        target_roots.append(root)
    (config_dir / "delegations.yaml").write_text(yaml.safe_dump(document, sort_keys=False))
    before = {root: snapshot(root) for root in target_roots}
    command = [
        sys.executable,
        "-m",
        "skill_delegator.cli",
        "resolve",
        "--json",
        "--config",
        str(config_dir),
    ]

    first = subprocess.run(
        command, cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False
    )
    second = subprocess.run(
        command, cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False
    )

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert [item["id"] for item in payload["targets"]] == ["reviewer", "worker"]
    assert all(item["links"][0]["artifact_id"] == "example/hello" for item in payload["targets"])
    assert {root: snapshot(root) for root in target_roots} == before
