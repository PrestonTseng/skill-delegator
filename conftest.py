"""Repository-level pytest guard for generic tests.

This module intentionally parses YAML directly. Importing production configuration here would
couple test startup to cache-affecting behavior and weaken the pre-test safety boundary.
"""

from __future__ import annotations

import hashlib
import os
import stat
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
SAFE_CONFIG_SHA256 = {
    "README.md": "d876696c47f1ed6e61a99689d0b5841c01c1ff04cb18dd2500cea4bdce55c160",
    "authority.yaml": "f3ac0bd41f8aaeb7af4e0d84231e03fd700273a2ad02877183d7e8ce615236b9",
    "delegations.yaml": "6754b8bdb54359aa44a1957065366f08fd607481040871bf4d428258e13717af",
    "pool.yaml": "e88cb540b9e6cc3e58f0f4198a6dcfcaaada225f57d49838741173ca9d30a76b",
    "skill-lock.yaml": "69ae60e70fb90304104e3570d113fd48a37462f326400611f6ffe3896d3fb8cf",
    "sources.yaml": "7e7b34ae4d0b5871fbe4fcfb172e493ad05a208654b1be9cdee2eaa80d3b0000",
}


class UnsafeGenericConfig(ValueError):
    pass


def _read_mapping(name: str, content: bytes) -> dict[str, Any]:
    try:
        document = yaml.safe_load(content.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        raise UnsafeGenericConfig(f"cannot safely read {name}: {exc}") from exc
    if not isinstance(document, dict):
        raise UnsafeGenericConfig(f"{name} must contain a mapping")
    return document


def _read_descriptor(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    while chunk := os.read(descriptor, 128 * 1024):
        chunks.append(chunk)
    return b"".join(chunks)


def _exact_safe_config(config: Path) -> dict[str, bytes]:
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    config_descriptor = os.open(config, directory_flags)
    try:
        actual_entries = set(os.listdir(config_descriptor))
        expected_entries = set(SAFE_CONFIG_SHA256)
        if actual_entries != expected_entries:
            missing = sorted(expected_entries - actual_entries)
            extra = sorted(actual_entries - expected_entries)
            raise UnsafeGenericConfig(
                f"config entry set is not exact (missing={missing}, extra={extra})"
            )

        documents: dict[str, bytes] = {}
        file_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        for name, expected_hash in SAFE_CONFIG_SHA256.items():
            descriptor = os.open(name, file_flags, dir_fd=config_descriptor)
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise UnsafeGenericConfig(f"config/{name} must be a non-symlink regular file")
                content = _read_descriptor(descriptor)
            finally:
                os.close(descriptor)
            if hashlib.sha256(content).hexdigest() != expected_hash:
                raise UnsafeGenericConfig(f"config/{name} does not match the accepted safe example")
            documents[name] = content

        if set(os.listdir(config_descriptor)) != expected_entries:
            raise UnsafeGenericConfig("config entry set changed during safety validation")
        return documents
    finally:
        os.close(config_descriptor)


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
    exact_config = _exact_safe_config(config)
    authority = _read_mapping("authority.yaml", exact_config["authority.yaml"])
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

    sources = _read_mapping("sources.yaml", exact_config["sources.yaml"]).get("sources")
    if not isinstance(sources, list) or not sources:
        raise UnsafeGenericConfig("sources.yaml must contain a non-empty sources list")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise UnsafeGenericConfig(f"source {index} must be a mapping")
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id:
            raise UnsafeGenericConfig(f"source {index} id must be a non-empty string")
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

    configured_id_values = [source["id"] for source in sources]
    if len(configured_id_values) != len(set(configured_id_values)):
        raise UnsafeGenericConfig("sources.yaml source ids must be unique")
    configured_ids = set(configured_id_values)
    pool = _read_mapping("pool.yaml", exact_config["pool.yaml"]).get("skills")
    if not isinstance(pool, list) or not pool or not all(isinstance(item, str) for item in pool):
        raise UnsafeGenericConfig("pool.yaml must contain a non-empty string skills list")
    if any(item.split("/", 1)[0] not in configured_ids for item in pool):
        raise UnsafeGenericConfig("pool.yaml references a source outside safe sources")
    pool_ids = set(pool)

    targets = _read_mapping("delegations.yaml", exact_config["delegations.yaml"]).get("targets")
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

    lock_sources = _read_mapping("skill-lock.yaml", exact_config["skill-lock.yaml"]).get("sources")
    if not isinstance(lock_sources, list):
        raise UnsafeGenericConfig("skill-lock.yaml sources must be a list")
    lock_source_ids: list[str] = []
    for source in lock_sources:
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            raise UnsafeGenericConfig("skill-lock.yaml source entries are malformed")
        lock_source_ids.append(source["source_id"])
    if len(lock_source_ids) != len(set(lock_source_ids)) or set(lock_source_ids) != configured_ids:
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
