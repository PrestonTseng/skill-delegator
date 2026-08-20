from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.fixture_safety import (
    FixtureSafetyError,
    assert_mutation_fixture_confined,
    copy_mutation_fixture,
    mutation_policy_violations,
    rewrite_mutation_config,
)

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_copied_mutation_fixture_rewrites_every_configured_path_under_tmp_path(
    tmp_path: Path,
) -> None:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)

    assert_mutation_fixture_confined(project, tmp_path)
    sources = yaml.safe_load((project / "config" / "sources.yaml").read_text())
    delegations = yaml.safe_load((project / "config" / "delegations.yaml").read_text())
    assert all(not Path(source["location"]).is_absolute() for source in sources["sources"])
    assert all(not Path(target["root"]).is_absolute() for target in delegations["targets"])


def test_multi_file_mutation_fixture_rewrites_every_target_under_tmp_path(
    tmp_path: Path,
) -> None:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)
    config = project / "config"
    legacy_path = config / "delegations.yaml"
    targets = yaml.safe_load(legacy_path.read_text(encoding="utf-8"))["targets"]
    legacy_path.unlink()
    delegation_dir = config / "delegations"
    delegation_dir.mkdir()
    expected_ids = {target["id"] for target in targets}
    for target in targets:
        target["root"] = f"/external/{target['id']}"
        (delegation_dir / f"{target['id']}.yaml").write_text(
            yaml.safe_dump({"schema_version": 1, "target": target}, sort_keys=False),
            encoding="utf-8",
        )

    rewrite_mutation_config(config)

    assert_mutation_fixture_confined(project, tmp_path)
    actual_ids: set[str] = set()
    for path in sorted(delegation_dir.glob("*.yaml")):
        target = yaml.safe_load(path.read_text(encoding="utf-8"))["target"]
        actual_ids.add(target["id"])
        root = (config / target["root"]).resolve()
        assert root.is_relative_to(project)
        assert root == project / "var" / "example-targets" / target["id"]
    assert actual_ids == expected_ids


def test_mutation_fixture_refuses_external_target(tmp_path: Path) -> None:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)
    path = project / "config" / "delegations.yaml"
    document = yaml.safe_load(path.read_text())
    document["targets"][0]["root"] = "/opt/data/skills"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    with pytest.raises(FixtureSafetyError, match="escapes pytest tmp_path lexically"):
        assert_mutation_fixture_confined(project, tmp_path)


def test_mutation_fixture_refuses_existing_ancestor_escape(tmp_path: Path) -> None:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (project / "var").symlink_to(outside, target_is_directory=True)

    with pytest.raises(FixtureSafetyError, match="existing ancestor"):
        assert_mutation_fixture_confined(project, tmp_path)


@pytest.mark.parametrize("mode", ("both", "neither"))
def test_mutation_fixture_requires_exactly_one_delegation_form(tmp_path: Path, mode: str) -> None:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)
    config = project / "config"
    legacy = config / "delegations.yaml"
    directory = config / "delegations"
    if mode == "both":
        directory.mkdir()
        (directory / "worker.yaml").write_text(
            "schema_version: 1\ntarget:\n  id: worker\n  root: ../target\n  grants: []\n",
            encoding="utf-8",
        )
    else:
        legacy.unlink()

    with pytest.raises(FixtureSafetyError, match="exactly one"):
        assert_mutation_fixture_confined(project, tmp_path)


@pytest.mark.parametrize("entry_kind", ("directory-symlink", "file-symlink"))
def test_mutation_fixture_rejects_symlinked_delegation_entries(
    tmp_path: Path, entry_kind: str
) -> None:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)
    config = project / "config"
    legacy = config / "delegations.yaml"
    if entry_kind == "directory-symlink":
        outside = tmp_path / "outside-delegations"
        outside.mkdir()
        legacy.unlink()
        (config / "delegations").symlink_to(outside, target_is_directory=True)
    else:
        document = yaml.safe_load(legacy.read_text(encoding="utf-8"))
        legacy.unlink()
        directory = config / "delegations"
        directory.mkdir()
        outside = tmp_path / "outside.yaml"
        outside.write_text(
            yaml.safe_dump({"schema_version": 1, "target": document["targets"][0]}),
            encoding="utf-8",
        )
        (directory / "worker.yaml").symlink_to(outside)

    with pytest.raises(FixtureSafetyError, match="non-symlink"):
        assert_mutation_fixture_confined(project, tmp_path)


@pytest.mark.parametrize(
    ("name", "contents", "message"),
    (
        ("worker.yaml", "target: [\n", "cannot safely parse"),
        ("notes.txt", "ignored\n", "regular YAML file"),
        ("nested.yaml", None, "regular YAML file"),
    ),
)
def test_mutation_fixture_rejects_malformed_or_non_regular_mixed_entries(
    tmp_path: Path, name: str, contents: str | None, message: str
) -> None:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)
    config = project / "config"
    (config / "delegations.yaml").unlink()
    directory = config / "delegations"
    directory.mkdir()
    (directory / "alpha.yaml").write_text(
        "schema_version: 1\ntarget:\n  id: alpha\n  root: ../target\n  grants: []\n",
        encoding="utf-8",
    )
    hostile = directory / name
    if contents is None:
        hostile.mkdir()
    else:
        hostile.write_text(contents, encoding="utf-8")

    with pytest.raises(FixtureSafetyError, match=message):
        assert_mutation_fixture_confined(project, tmp_path)


def test_mutation_policy_audits_every_test_module_with_the_collection_gate() -> None:
    violations = [
        violation
        for path in sorted((REPOSITORY_ROOT / "tests").rglob("test_*.py"))
        if path != Path(__file__)
        for violation in mutation_policy_violations(path, REPOSITORY_ROOT)
    ]

    assert violations == []


def test_policy_detects_direct_alias_and_wrapper_repository_config_invocations(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test_forbidden.py"
    path.write_text(
        """from pathlib import Path
import subprocess as process
from skill_delegator.cli import main as invoke

REPOSITORY_ROOT = Path(__file__).parents[2]
AUTHORITY = REPOSITORY_ROOT / "config"
ARGS = ["apply", "--config", str(AUTHORITY)]

def wrapper(arguments):
    return process.run(arguments)

def test_direct():
    invoke(["apply", "--config", str(REPOSITORY_ROOT / "config")])

def test_wrapper():
    wrapper(ARGS)
""",
        encoding="utf-8",
    )

    violations = mutation_policy_violations(path, REPOSITORY_ROOT)

    assert len(violations) == 1
    assert "repository config" in violations[0]


def test_pytest_policy_gate_rejects_repository_config_before_test_body(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "mutation-sentinel"
    path = tmp_path / "test_forbidden_repository_mutation.py"
    path.write_text(
        f"""from pathlib import Path
import subprocess

REPOSITORY_ROOT = Path({os.fspath(REPOSITORY_ROOT)!r})
CONFIG = REPOSITORY_ROOT / "config"

def fake_run(arguments):
    Path({os.fspath(sentinel)!r}).write_text("body executed")

def invoke(arguments):
    return subprocess.run(arguments)

def test_forbidden():
    subprocess.run = fake_run
    invoke(["apply", "--config", str(CONFIG)])
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "conftest", os.fspath(path)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert "mutation-safety policy" in result.stdout + result.stderr
    assert not sentinel.exists()
