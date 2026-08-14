from __future__ import annotations

import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).parents[2]


def _example(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    shutil.copytree(REPOSITORY_ROOT / "config", project / "config")
    shutil.copytree(
        REPOSITORY_ROOT / "tests" / "fixtures" / "example-source",
        project / "tests" / "fixtures" / "example-source",
    )
    return project


def _run(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skill_delegator.cli", *arguments],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("mutation", "command", "expected"),
    [
        ({"source_id": "evil"}, ("resolve", "--json"), 2),
        ({"canonical_id": "example/../escape"}, ("resolve", "--json"), 2),
        ({"path": "../hello"}, ("resolve", "--json"), 2),
        ({"runtime_name": "../../hostile\nname"}, ("resolve", "--json"), 2),
        ({"sha256": "0" * 64}, ("apply",), 3),
        ({"tree_hash": "0" * 64}, ("apply",), 3),
    ],
    ids=(
        "source-identity",
        "canonical-name",
        "locked-path",
        "runtime-name",
        "skill-hash",
        "tree-hash",
    ),
)
def test_tampered_lock_fails_closed_without_target_mutation(
    tmp_path: Path, mutation: dict[str, str], command: tuple[str, ...], expected: int
) -> None:
    project = _example(tmp_path)
    path = project / "config" / "skill-lock.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    source = document["sources"][0]
    skill = source["skills"][0]
    for key, value in mutation.items():
        (source if key in {"source_id", "tree_hash"} else skill)[key] = value
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    lock_before = copy.deepcopy(document)

    result = _run(project, *command)

    assert result.returncode == expected, (result.stdout, result.stderr)
    assert result.stdout == ""
    assert result.stderr
    assert "Traceback" not in result.stderr
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == lock_before
    assert not (project / "var" / "example-targets").exists()


@pytest.mark.parametrize(
    "managed_bytes",
    [
        b"{not-json\n",
        b"{}\n",
        b'{"schema_version":1,"schema_version":1}\n',
        b'{"schema_version":true,"manager":"skill-delegator","cache_root":"/tmp/x","entries":[]}\n',
    ],
    ids=("malformed-json", "missing-fields", "duplicate-key", "boolean-schema-version"),
)
def test_malformed_managed_state_blocks_plan_without_mutation(
    tmp_path: Path, managed_bytes: bytes
) -> None:
    project = _example(tmp_path)
    assert _run(project, "lock").returncode == 0
    assert _run(project, "apply").returncode == 0
    managed = project / "var" / "example-targets" / "worker" / ".skill-delegator" / "managed.json"
    managed.write_bytes(managed_bytes)
    before = managed.read_bytes()

    result = _run(project, "plan", "--json")

    assert result.returncode == 3
    assert "Traceback" not in result.stderr
    assert managed.read_bytes() == before


@pytest.mark.parametrize("replacement", ["broken", "wrong"])
def test_broken_or_wrong_managed_link_blocks_plan_without_repair(
    tmp_path: Path, replacement: str
) -> None:
    project = _example(tmp_path)
    assert _run(project, "lock").returncode == 0
    assert _run(project, "apply").returncode == 0
    link = project / "var" / "example-targets" / "worker" / "example" / "hello"
    link.unlink()
    link.symlink_to(tmp_path / ("missing" if replacement == "broken" else "outside"))
    if replacement == "wrong":
        (tmp_path / "outside").mkdir()
    raw_before = link.readlink()

    result = _run(project, "plan", "--json")

    assert result.returncode == 3
    assert link.is_symlink()
    assert link.readlink() == raw_before


def test_lock_rejects_hostile_runtime_name_discovered_from_source(tmp_path: Path) -> None:
    project = _example(tmp_path)
    manifest = project / "tests" / "fixtures" / "example-source" / "hello" / "SKILL.md"
    manifest.write_text(
        "---\nname: ../../hostile\\nname\ndescription: hostile fixture\n---\n",
        encoding="utf-8",
    )

    result = _run(project, "lock")

    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("Lock error:")
    assert "Traceback" not in result.stderr
    assert not (project / "var" / "example-targets").exists()
