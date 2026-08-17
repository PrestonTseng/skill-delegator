"""Fail-closed confinement helpers for tests that can write through the CLI."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import yaml

MUTATION_CAPABLE_COMMANDS = frozenset({"apply", "lock", "update", "verify"})


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

    delegations_path = config / "delegations.yaml"
    delegations = _document(delegations_path)
    targets = delegations.get("targets")
    if not isinstance(targets, list) or not targets:
        raise FixtureSafetyError("delegations.yaml must contain a non-empty targets list")
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise FixtureSafetyError("every copied target must have a string id")
        target["root"] = f"../var/example-targets/{target['id']}"
    delegations_path.write_text(yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8")


def copy_mutation_config(repository_root: Path, project: Path) -> Path:
    config = project / "config"
    shutil.copytree(repository_root / "config", config)
    rewrite_mutation_config(config)
    return config


def copy_mutation_fixture(repository_root: Path, tmp_path: Path, name: str = "project") -> Path:
    project = tmp_path / name
    copy_mutation_config(repository_root, project)
    shutil.copytree(
        repository_root / "tests" / "fixtures" / "example-source",
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

    delegations = _document(config / "delegations.yaml").get("targets")
    if not isinstance(delegations, list) or not delegations:
        raise FixtureSafetyError("delegations.yaml must contain a non-empty targets list")
    for index, target in enumerate(delegations):
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
