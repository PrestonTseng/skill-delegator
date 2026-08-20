from __future__ import annotations

import json
import os
import shutil
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
from tests.fixture_safety import run_cli

REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "tests" / "fixtures" / "safe-config"
_SHA = "a" * 64


def authority(tmp_path: Path, pool: tuple[str, ...], grants: tuple[str, ...]) -> AuthorityConfig:
    source_ids = sorted({item.split("/", 1)[0] for item in (*pool, *grants)})
    return AuthorityConfig(
        "test",
        True,
        "none",
        tuple(
            SourceSpec(item, "filesystem", tmp_path / item, PurePosixPath("."))
            for item in source_ids
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
        resolve_desired_state(
            config, SkillLock(1, (LockedSource("one", "filesystem", None, "f" * 64, ()),))
        )


def test_rejects_duplicate_grants_even_when_models_bypass_yaml_schema(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/tool",), ("one/tool", "one/tool"))
    lock = SkillLock(1, (locked("one", "one/tool", "tool", "tool"),))
    with pytest.raises(ResolutionError, match="duplicate grant.*one/tool"):
        resolve_desired_state(config, lock)


def test_rejects_duplicate_runtime_name_per_target_across_sources(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/a", "two/b"), ("one/a", "two/b"))
    lock = SkillLock(
        1,
        (locked("one", "one/a", "shared", "a"), locked("two", "two/b", "shared", "b")),
    )
    with pytest.raises(ResolutionError, match="duplicate runtime name.*shared"):
        resolve_desired_state(config, lock)


def test_rejects_normalized_target_escape(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/../../escape",), ("one/../../escape",))
    lock = SkillLock(1, (locked("one", "one/../../escape", "escape", "escape"),))
    with pytest.raises(ResolutionError, match="invalid canonical|outside target root"):
        resolve_desired_state(config, lock)


def test_rejects_normalized_target_path_collision(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/same",), ("one/same",))
    shared_root = tmp_path / "shared-target"
    config = replace(
        config,
        targets=(
            TargetSpec("first", shared_root, ("one/same",)),
            TargetSpec("second", shared_root, ("one/same",)),
        ),
    )
    lock = SkillLock(1, (locked("one", "one/same", "same", "same"),))
    with pytest.raises(ResolutionError, match="target path collision"):
        resolve_desired_state(config, lock)


def test_equal_paths_are_isolated_by_multi_file_deployment_scope(tmp_path: Path) -> None:
    config = authority(tmp_path, ("one/same",), ("one/same",))
    shared_root = tmp_path / "shared-target"
    targets = (
        TargetSpec("first", shared_root, ("one/same",), "delegations/first.yaml"),
        TargetSpec("second", shared_root, ("one/same",), "delegations/second.yaml"),
    )
    lock = SkillLock(1, (locked("one", "one/same", "same", "same"),))

    state = resolve_desired_state(
        replace(config, targets=targets, delegation_mode="multiple"), lock
    )

    assert tuple(target.id for target in state.targets) == ("first", "second")

    legacy_targets = tuple(replace(target, deployment_scope="shared") for target in targets)
    with pytest.raises(ResolutionError, match="target path collision"):
        resolve_desired_state(
            replace(config, targets=legacy_targets, delegation_mode="single"), lock
        )


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
        "resolve",
        "--json",
        "--config",
        str(config_dir),
    ]

    first = run_cli(config_dir, tmp_path, command, cwd=REPOSITORY_ROOT)
    second = run_cli(config_dir, tmp_path, command, cwd=REPOSITORY_ROOT)

    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert [item["id"] for item in payload["targets"]] == ["reviewer", "worker"]
    assert all(item["links"][0]["artifact_id"] == "example/hello" for item in payload["targets"])
    assert {root: snapshot(root) for root in target_roots} == before


@pytest.mark.parametrize(
    ("lock_mutation", "message"),
    (
        ({"source_id": "evil"}, "missing=['example'], extra=['evil']"),
        ({"canonical_id": "evil/hello"}, "artifact evil/hello is enclosed by source example"),
        ({"path": "different"}, "locked path different does not match canonical suffix hello"),
        ({"path": "../hello"}, "skill-lock.yaml at sources.0.skills.0.path:"),
    ),
    ids=("evil-source", "wrong-prefix", "wrong-relative-path", "path-escape"),
)
def test_resolve_cli_rejects_source_authority_binding_without_output_or_writes(
    tmp_path: Path, lock_mutation: dict[str, str], message: str
) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)
    lock_path = config_dir / "skill-lock.yaml"
    document = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    source = document["sources"][0]
    skill = source["skills"][0]
    if "source_id" in lock_mutation:
        source["source_id"] = lock_mutation["source_id"]
    if "canonical_id" in lock_mutation:
        skill["canonical_id"] = lock_mutation["canonical_id"]
    if "path" in lock_mutation:
        skill["path"] = lock_mutation["path"]
    lock_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    target_roots = (
        tmp_path / "var" / "example-targets" / "worker",
        tmp_path / "var" / "example-targets" / "reviewer",
    )

    result = run_cli(
        config_dir,
        tmp_path,
        [
            "resolve",
            "--json",
            "--config",
            str(config_dir),
        ],
        cwd=REPOSITORY_ROOT,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert message in result.stderr
    assert len(result.stderr) <= 512
    assert "Traceback" not in result.stderr
    assert all(not root.exists() for root in target_roots)
