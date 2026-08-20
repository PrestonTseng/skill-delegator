from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from tests.fixture_safety import (
    FixtureSafetyError,
    assert_mutation_fixture_confined,
    copy_mutation_fixture,
    rewrite_mutation_config,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
MUTATION_COMMANDS = {"apply", "lock", "update", "verify"}


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


def _is_repository_config_reference(node: ast.AST, aliases: set[str]) -> bool:
    text = ast.unparse(node)
    return ("REPOSITORY_ROOT" in text and "config" in text) or any(
        alias in text for alias in aliases
    )


def test_mutation_capable_tests_never_copy_repository_config_without_safety_helper() -> None:
    violations: list[str] = []
    for path in sorted((REPOSITORY_ROOT / "tests").rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        strings = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        if not strings.intersection(MUTATION_COMMANDS):
            continue
        aliases = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
            if isinstance(target, ast.Name)
            and node.value is not None
            and "REPOSITORY_ROOT" in ast.unparse(node.value)
            and "config" in ast.unparse(node.value)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            function = ast.unparse(node.func)
            if function.endswith("copytree") and _is_repository_config_reference(
                node.args[0], aliases
            ):
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
    assert violations == [], (
        "mutation-capable tests must use tests.fixture_safety copied/config confinement helper: "
        + ", ".join(violations)
    )
