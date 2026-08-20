"""Fail-closed confinement helpers for tests that can write through the CLI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from skill_delegator import cli

MUTATION_CAPABLE_COMMANDS = frozenset({"apply", "lock", "update", "verify"})
SAFE_CONFIG = Path(__file__).parent / "fixtures" / "safe-config"


class FixtureSafetyError(AssertionError):
    """A mutation fixture can reach outside its pytest temporary root."""


def _document(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise FixtureSafetyError(f"cannot safely parse {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise FixtureSafetyError(f"{path.name} must contain a mapping")
    return value


def _lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _require_confined(path: Path, boundary: Path, label: str) -> None:
    candidate = _lexical(path)
    root = _lexical(boundary)
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise FixtureSafetyError(f"{label} escapes pytest tmp_path lexically: {candidate}") from exc

    current = root
    for part in relative.parts:
        current = current / part
        if not os.path.lexists(current):
            continue
        resolved = current.resolve(strict=False)
        try:
            resolved.relative_to(root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise FixtureSafetyError(
                f"{label} escapes pytest tmp_path through existing ancestor {current}"
            ) from exc


def _configured_path(config: Path, raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise FixtureSafetyError(f"{label} must be a non-empty path string")
    path = Path(raw)
    return path if path.is_absolute() else config / path


def _delegation_targets(config: Path) -> tuple[tuple[Path, dict[str, Any]], ...]:
    legacy_path = config / "delegations.yaml"
    directory = config / "delegations"
    legacy_exists = os.path.lexists(legacy_path)
    directory_exists = os.path.lexists(directory)
    if legacy_exists == directory_exists:
        raise FixtureSafetyError(
            "mutation fixture must contain exactly one of delegations.yaml or delegations/"
        )

    if legacy_exists:
        document = _document(legacy_path)
        targets = document.get("targets")
        if not isinstance(targets, list) or not targets:
            raise FixtureSafetyError("delegations.yaml must contain a non-empty targets list")
        return tuple((legacy_path, target) for target in targets)

    if directory.is_symlink() or not directory.is_dir():
        raise FixtureSafetyError("delegations/ must be a non-symlink directory")
    paths = sorted(directory.iterdir(), key=lambda path: os.fsencode(path.name))
    if not paths:
        raise FixtureSafetyError("delegations/ must contain at least one target file")
    targets_with_paths: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        if path.suffix != ".yaml" or path.is_symlink() or not path.is_file():
            raise FixtureSafetyError(
                f"delegations/{path.name} must be a non-symlink regular YAML file"
            )
        target = _document(path).get("target")
        if not isinstance(target, dict):
            raise FixtureSafetyError(f"delegations/{path.name} must contain a target mapping")
        targets_with_paths.append((path, target))
    return tuple(targets_with_paths)


def rewrite_mutation_config(config: Path) -> None:
    """Rewrite every configured source and target to the copied pytest project."""
    sources_path = config / "sources.yaml"
    sources = _document(sources_path)
    entries = sources.get("sources")
    if not isinstance(entries, list) or not entries:
        raise FixtureSafetyError("sources.yaml must contain a non-empty sources list")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise FixtureSafetyError("every copied source must have a string id")
        source_id = entry["id"]
        fixture_name = "example-source" if source_id == "example" else f"{source_id}-source"
        entry["location"] = f"../tests/fixtures/{fixture_name}"
    sources_path.write_text(yaml.safe_dump(sources, sort_keys=False), encoding="utf-8")

    targets_with_paths = _delegation_targets(config)
    legacy = targets_with_paths[0][0] == config / "delegations.yaml"
    for path, target in targets_with_paths:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise FixtureSafetyError("every copied target must have a string id")
        target["root"] = f"../var/example-targets/{target['id']}"
        if not legacy:
            document = _document(path)
            document["target"] = target
            path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    if legacy:
        document = _document(targets_with_paths[0][0])
        document["targets"] = [target for _, target in targets_with_paths]
        targets_with_paths[0][0].write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )


def copy_mutation_config(repository_root: Path, project: Path) -> Path:
    """Copy fixed generic authority data; retain the first argument for caller compatibility."""
    del repository_root
    config = project / "config"
    shutil.copytree(SAFE_CONFIG, config)
    rewrite_mutation_config(config)
    return config


def copy_mutation_fixture(repository_root: Path, tmp_path: Path, name: str = "project") -> Path:
    project = tmp_path / name
    copy_mutation_config(repository_root, project)
    shutil.copytree(
        Path(__file__).parent / "fixtures" / "example-source",
        project / "tests" / "fixtures" / "example-source",
    )
    assert_mutation_fixture_confined(project, tmp_path)
    return project


def assert_mutation_fixture_confined(project: Path, tmp_path: Path) -> None:
    """Assert all write-capable roots remain confined, including through existing ancestors."""
    config = project / "config"
    _require_confined(project, tmp_path, "fixture project")

    sources = _document(config / "sources.yaml").get("sources")
    if not isinstance(sources, list) or not sources:
        raise FixtureSafetyError("sources.yaml must contain a non-empty sources list")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise FixtureSafetyError(f"source {index} must be a mapping")
        location = _configured_path(config, source.get("location"), f"source {index}")
        _require_confined(location, tmp_path, f"source {index}")
        skill_root = source.get("skill_root", ".")
        if not isinstance(skill_root, str):
            raise FixtureSafetyError(f"source {index} skill_root must be a string")
        _require_confined(location / skill_root, tmp_path, f"source {index} skill_root")

    targets_with_paths = _delegation_targets(config)
    for index, (_, target) in enumerate(targets_with_paths):
        if not isinstance(target, dict):
            raise FixtureSafetyError(f"target {index} must be a mapping")
        root = _configured_path(config, target.get("root"), f"target {index}")
        _require_confined(root, tmp_path, f"target {index}")

    for relative, label in (
        ("var/cache/sources", "derived source cache"),
        ("var/receipts", "derived receipt root"),
    ):
        _require_confined(project / relative, tmp_path, label)


def assert_before_mutation(project: Path, tmp_path: Path, command: str) -> None:
    if command in MUTATION_CAPABLE_COMMANDS:
        assert_mutation_fixture_confined(project, tmp_path)


def invoke_platform_cli(cli_module: Any, arguments: list[str]) -> int:
    """Invoke only the no-config platform/help probes through an explicit safe path."""
    if arguments not in (["--help"], ["validate"]):
        raise FixtureSafetyError("platform CLI helper only permits --help or validate")
    return cli_module.main(arguments)


def run_cli(
    config: Path,
    tmp_path: Path,
    arguments: list[str],
    *,
    cwd: Path | None = None,
    text: bool = True,
) -> int | subprocess.CompletedProcess[Any]:
    """Dispatch every configured production CLI call through one mutation boundary."""
    if not arguments:
        raise FixtureSafetyError("CLI arguments must include a command")
    command = arguments[0]
    if command in MUTATION_CAPABLE_COMMANDS:
        if "--config" not in arguments:
            raise FixtureSafetyError("mutation-capable CLI arguments must include --config")
        configured = Path(arguments[arguments.index("--config") + 1])
        if _lexical(configured) != _lexical(config):
            raise FixtureSafetyError("mutation-capable CLI config does not match wrapper config")
    if cwd is None:
        assert_before_mutation(config.parent, tmp_path, command)
        return cli.main(arguments)
    process_arguments = [sys.executable, "-m", "skill_delegator.cli", *arguments]
    assert_before_mutation(config.parent, tmp_path, command)
    return subprocess.run(
        process_arguments,
        cwd=cwd,
        capture_output=True,
        text=text,
        check=False,
    )


def run_git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run only git for isolated fixture setup and inspection."""
    return subprocess.run(
        ["git", "-C", os.fspath(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def build_release_artifacts(project: Path, dist: Path) -> None:
    """Run only the package build used by the release-artifact test."""
    subprocess.run(
        ["uv", "build", "--out-dir", os.fspath(dist)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )


def mutation_policy_violations(path: Path, repository_root: Path) -> tuple[str, ...]:
    """Reject direct process/production-CLI reachability outside allowlisted helpers."""
    import ast

    del repository_root
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=os.fspath(path))
    except SyntaxError as exc:
        return (f"{path}:{exc.lineno}: cannot audit syntax",)
    violations: list[str] = []
    cli_module_aliases: set[str] = set()
    os_module_aliases: set[str] = set()
    subprocess_module_aliases: set[str] = set()
    subprocess_function_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".")[0]
                if alias.name == "subprocess":
                    subprocess_module_aliases.add(bound)
                elif alias.name == "skill_delegator.cli":
                    cli_module_aliases.add(alias.asname or alias.name)
                elif alias.name == "os":
                    os_module_aliases.add(bound)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "subprocess":
                subprocess_function_aliases.update(
                    alias.asname or alias.name for alias in node.names
                )
            elif node.module == "skill_delegator.cli":
                for alias in node.names:
                    if alias.name == "main":
                        violations.append(
                            f"{path}:{node.lineno}: direct production CLI entrypoint reachability is forbidden"
                        )
            elif node.module == "skill_delegator":
                for alias in node.names:
                    if alias.name == "cli":
                        cli_module_aliases.add(alias.asname or alias.name)

    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

    def is_narrow_safe_process_call(node: ast.Attribute) -> bool:
        call = parents.get(node)
        if not isinstance(call, ast.Call) or call.func is not node or not call.args:
            return False
        command = call.args[0]
        if not isinstance(command, (ast.List, ast.Tuple)) or not command.elts:
            return False
        first = command.elts[0]
        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            return False
        # Inspectable non-production process allowlist: fixture git and exact package build only.
        return first.value == "git" or (
            first.value == "uv"
            and len(command.elts) >= 2
            and isinstance(command.elts[1], ast.Constant)
            and command.elts[1].value == "build"
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if (
            node.attr == "main"
            and isinstance(node.value, ast.Name)
            and node.value.id in cli_module_aliases
        ):
            violations.append(
                f"{path}:{node.lineno}: direct production CLI entrypoint reachability is forbidden"
            )
        if (
            isinstance(node.value, ast.Name)
            and node.value.id in subprocess_module_aliases
            and node.attr in {"run", "call", "check_call", "check_output", "Popen"}
            and not is_narrow_safe_process_call(node)
        ):
            violations.append(
                f"{path}:{node.lineno}: direct process-launch reachability is forbidden"
            )
        if (
            isinstance(node.ctx, ast.Load)
            and isinstance(node.value, ast.Name)
            and node.value.id in os_module_aliases
            and (node.attr in {"system", "popen"} or node.attr.startswith(("exec", "spawn")))
        ):
            violations.append(
                f"{path}:{node.lineno}: direct process-launch reachability is forbidden"
            )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in subprocess_function_aliases
        ):
            violations.append(
                f"{path}:{node.lineno}: direct process-launch reachability is forbidden"
            )
    return tuple(dict.fromkeys(violations))
