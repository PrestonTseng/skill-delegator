"""Repository-level pytest guard for generic tests.

This module intentionally parses YAML directly. Importing production configuration here would
couple test startup to cache-affecting behavior and weaken the pre-test safety boundary.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).parent
DIAGNOSTIC = "pytest safety guard: refusing generic tests:"
EXPECTED_AUTHORITY = {
    "schema_version": 1,
    "authority": {
        "id": "main-example",
        "fail_closed": True,
        "fixture_policy": "safe-main-example",
    },
}


class UnsafeGenericConfig(ValueError):
    pass


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise UnsafeGenericConfig(f"cannot safely read {path.name}: {exc}") from exc
    if not isinstance(document, dict):
        raise UnsafeGenericConfig(f"{path.name} must contain a mapping")
    return document


def _lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _confined(path: Path, boundary: Path, label: str) -> None:
    candidate = _lexical(path)
    root = _lexical(boundary)
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise UnsafeGenericConfig(f"{label} is outside {root}") from exc

    resolved_root = root.resolve(strict=True)
    current = root
    for part in relative.parts:
        current = current / part
        if not os.path.lexists(current):
            continue
        try:
            current.resolve(strict=False).relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise UnsafeGenericConfig(
                f"{label} escapes through symlink ancestor {current}"
            ) from exc


def _configured_path(config: Path, raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise UnsafeGenericConfig(f"{label} must be a non-empty path string")
    path = Path(raw)
    return path if path.is_absolute() else config / path


def validate_repository_config() -> None:
    config = REPOSITORY_ROOT / "config"
    authority = _read_mapping(config / "authority.yaml")
    if authority != EXPECTED_AUTHORITY:
        raise UnsafeGenericConfig("authority.yaml is not the exact safe main-example contract")

    allowed_fixture_root = REPOSITORY_ROOT / "tests" / "fixtures"
    allowed_generated_source_root = REPOSITORY_ROOT / "var" / "cache" / "sources"
    for path, label in (
        (allowed_fixture_root, "example fixture root"),
        (allowed_generated_source_root, "generated source cache root"),
        (REPOSITORY_ROOT / "var" / "receipts", "generated receipt root"),
    ):
        _confined(path, REPOSITORY_ROOT, label)

    sources = _read_mapping(config / "sources.yaml").get("sources")
    if not isinstance(sources, list) or not sources:
        raise UnsafeGenericConfig("sources.yaml must contain a non-empty sources list")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise UnsafeGenericConfig(f"source {index} must be a mapping")
        location = _configured_path(config, source.get("location"), f"source {index}")
        lexical_location = _lexical(location)
        if not any(
            lexical_location.is_relative_to(_lexical(root))
            for root in (allowed_fixture_root, allowed_generated_source_root)
        ):
            raise UnsafeGenericConfig(f"source {index} is outside repository example roots")
        _confined(location, REPOSITORY_ROOT, f"source {index}")
        skill_root = source.get("skill_root", ".")
        if not isinstance(skill_root, str):
            raise UnsafeGenericConfig(f"source {index} skill_root must be a string")
        skill_path = _lexical(location / skill_root)
        if not any(
            skill_path.is_relative_to(_lexical(root))
            for root in (allowed_fixture_root, allowed_generated_source_root)
        ):
            raise UnsafeGenericConfig(f"source {index} skill_root is outside example roots")
        _confined(skill_path, REPOSITORY_ROOT, f"source {index} skill_root")

    configured_ids = {source.get("id") for source in sources}
    pool = _read_mapping(config / "pool.yaml").get("skills")
    if not isinstance(pool, list) or not pool or not all(isinstance(item, str) for item in pool):
        raise UnsafeGenericConfig("pool.yaml must contain a non-empty string skills list")
    if any(item.split("/", 1)[0] not in configured_ids for item in pool):
        raise UnsafeGenericConfig("pool.yaml references a source outside safe sources")
    pool_ids = set(pool)

    targets = _read_mapping(config / "delegations.yaml").get("targets")
    if not isinstance(targets, list) or not targets:
        raise UnsafeGenericConfig("delegations.yaml must contain a non-empty targets list")
    allowed_targets = _lexical(REPOSITORY_ROOT / "var" / "example-targets")
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise UnsafeGenericConfig(f"target {index} must be a mapping")
        root = _configured_path(config, target.get("root"), f"target {index}")
        if not _lexical(root).is_relative_to(allowed_targets):
            raise UnsafeGenericConfig(f"target {index} is outside repository var/example-targets")
        _confined(root, REPOSITORY_ROOT, f"target {index}")
        grants = target.get("grants")
        if not isinstance(grants, list) or not all(isinstance(item, str) for item in grants):
            raise UnsafeGenericConfig(f"target {index} grants must be a string list")
        if not set(grants).issubset(pool_ids):
            raise UnsafeGenericConfig(f"target {index} grants are outside the safe pool")

    lock_sources = _read_mapping(config / "skill-lock.yaml").get("sources")
    if not isinstance(lock_sources, list):
        raise UnsafeGenericConfig("skill-lock.yaml sources must be a list")
    if {
        source.get("source_id") for source in lock_sources if isinstance(source, dict)
    } != configured_ids:
        raise UnsafeGenericConfig("skill-lock.yaml source identities do not match safe sources")
    locked_ids: set[str] = set()
    for source in lock_sources:
        if not isinstance(source, dict) or not isinstance(source.get("skills"), list):
            raise UnsafeGenericConfig("skill-lock.yaml source entries are malformed")
        for skill in source["skills"]:
            raw = skill.get("path") if isinstance(skill, dict) else None
            canonical_id = skill.get("canonical_id") if isinstance(skill, dict) else None
            if not isinstance(raw, str) or Path(raw).is_absolute() or ".." in Path(raw).parts:
                raise UnsafeGenericConfig("skill-lock.yaml contains an escaping skill path")
            if not isinstance(canonical_id, str):
                raise UnsafeGenericConfig("skill-lock.yaml contains a malformed canonical id")
            locked_ids.add(canonical_id)
    if not pool_ids.issubset(locked_ids):
        raise UnsafeGenericConfig("safe pool is not present in skill-lock.yaml")


def pytest_sessionstart(session: pytest.Session) -> None:
    del session
    try:
        validate_repository_config()
    except (OSError, RuntimeError, UnsafeGenericConfig) as exc:
        pytest.exit(f"{DIAGNOSTIC} {exc}", returncode=4)
