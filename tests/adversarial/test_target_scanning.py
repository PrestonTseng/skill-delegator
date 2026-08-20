from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import yaml

from tests.fixture_safety import run_cli

REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "tests" / "fixtures" / "safe-config"


def _snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    if not os.path.lexists(root):
        return ()
    records: list[tuple[str, str, str]] = []

    def visit(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda item: os.fsencode(item.name)):
            path = Path(entry.path)
            relative = str(path.relative_to(root))
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                records.append((relative, "symlink", os.readlink(path)))
            elif stat.S_ISDIR(mode):
                records.append((relative, "directory", ""))
                visit(path)
            else:
                records.append((relative, "file", path.read_bytes().hex()))

    visit(root)
    return tuple(records)


def _project(tmp_path: Path, name: str) -> tuple[Path, Path, Path]:
    project = tmp_path / name
    config = project / "config"
    shutil.copytree(EXAMPLE_CONFIG, config)
    target = project / "var" / "example-targets" / "worker"
    delegations = yaml.safe_load((config / "delegations.yaml").read_text(encoding="utf-8"))
    delegations["targets"] = [delegations["targets"][0]]
    (config / "delegations.yaml").write_text(
        yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8"
    )
    lock = yaml.safe_load((config / "skill-lock.yaml").read_text(encoding="utf-8"))
    revision = lock["sources"][0]["tree_hash"]
    source = project / "var" / "cache" / "sources" / "example" / revision / "hello"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("fixture", encoding="utf-8")
    return config, target, source


def _metadata(target: Path, source: Path) -> None:
    directory = target / ".skill-delegator"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "managed.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "manager": "skill-delegator",
                "cache_root": str(source.parents[2]),
                "entries": [
                    {
                        "artifact_id": "example/hello",
                        "source_path": str(source),
                        "content_sha256": "d38c385a71ef3a3ef674f7b6e2d5d9713b1faa27f1a30f14738ad49aadd512ec",
                    }
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def _run(config: Path, *, json_output: bool) -> subprocess.CompletedProcess[bytes]:
    command = ["plan", "--config", str(config)]
    if json_output:
        command.append("--json")
    return run_cli(config, config.parent.parent, command, cwd=REPOSITORY_ROOT, text=False)


def test_plan_cli_exit_codes_repeatable_output_and_zero_mutation_for_all_paths(
    tmp_path: Path,
) -> None:
    change_config, change_target, _ = _project(tmp_path, "change")
    change_target.mkdir(parents=True)
    (change_target / "sentinel").write_text("keep", encoding="utf-8")

    converged_config, converged_target, converged_source = _project(tmp_path, "converged")
    (converged_target / "example").mkdir(parents=True)
    (converged_target / "example" / "hello").symlink_to(converged_source)
    _metadata(converged_target, converged_source)

    blocked_config, blocked_target, blocked_source = _project(tmp_path, "blocked")
    (blocked_target / "example").mkdir(parents=True)
    (blocked_target / "example" / "hello").symlink_to(blocked_target / "missing")
    _metadata(blocked_target, blocked_source)

    cases = (
        (change_config, change_target, 1, "CREATE"),
        (converged_config, converged_target, 0, "KEEP"),
        (blocked_config, blocked_target, 3, "blocked"),
    )
    for config, target, exit_code, marker in cases:
        before = _snapshot(target)
        first = _run(config, json_output=True)
        middle = _snapshot(target)
        second = _run(config, json_output=True)
        after = _snapshot(target)

        assert first.returncode == second.returncode == exit_code
        assert first.stdout == second.stdout
        assert first.stderr == second.stderr == b""
        assert marker.encode() in first.stdout
        assert json.loads(first.stdout)
        assert before == middle == after

    text_before = _snapshot(change_target)
    first_text = _run(change_config, json_output=False)
    second_text = _run(change_config, json_output=False)
    assert first_text.returncode == second_text.returncode == 1
    assert first_text.stdout == second_text.stdout
    assert b"CREATE worker example/hello" in first_text.stdout
    assert _snapshot(change_target) == text_before


def test_plan_cli_blocks_managed_link_that_escapes_locked_source_expectation(
    tmp_path: Path,
) -> None:
    config, target, source = _project(tmp_path, "escape")
    outside = tmp_path / "outside"
    outside.mkdir()
    (target / "example").mkdir(parents=True)
    (target / "example" / "hello").symlink_to(outside)
    _metadata(target, source)
    metadata_path = target / ".skill-delegator" / "managed.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["cache_root"] = str(tmp_path)
    metadata["entries"][0]["source_path"] = str(outside)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    before = _snapshot(target)

    result = _run(config, json_output=True)

    assert result.returncode == 3
    assert result.stderr == b""
    document = json.loads(result.stdout)
    assert document["blocked"]
    assert any(
        "manager cache root differs from locked cache root" in blocker
        for blocker in document["blocked"]
    )
    assert not any(operation["action"] == "REPLACE" for operation in document["operations"])
    assert _snapshot(target) == before


def test_non_fixture_plan_blocks_symlinked_target_ancestor_without_target_writes(
    tmp_path: Path,
) -> None:
    config, configured_target, _ = _project(tmp_path, "symlinked-target-ancestor")
    authority_path = config / "authority.yaml"
    authority = yaml.safe_load(authority_path.read_text(encoding="utf-8"))
    authority["authority"].update({"id": "non-fixture", "fixture_policy": "none"})
    authority_path.write_text(yaml.safe_dump(authority, sort_keys=False), encoding="utf-8")

    outside = tmp_path / "outside-targets"
    outside.mkdir()
    linked_parent = configured_target.parent
    linked_parent.parent.mkdir(parents=True, exist_ok=True)
    linked_parent.symlink_to(outside, target_is_directory=True)
    before = _snapshot(outside)

    first = _run(config, json_output=True)
    middle = _snapshot(outside)
    second = _run(config, json_output=True)
    after = _snapshot(outside)

    assert first.returncode == second.returncode == 3
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == b""
    assert "target root contains a symlink" in json.loads(first.stdout)["blocked"][0]
    assert before == middle == after
