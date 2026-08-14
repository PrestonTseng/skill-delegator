"""Strict YAML and JSON Schema configuration loader."""

from __future__ import annotations

import json
import os
import re
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from skill_delegator.errors import ConfigError
from skill_delegator.models import AuthorityConfig, PoolSpec, SourceSpec, TargetSpec

_CONFIG_SCHEMAS = {
    "authority.yaml": "authority.schema.json",
    "sources.yaml": "sources.schema.json",
    "pool.yaml": "pool.schema.json",
    "delegations.yaml": "delegations.schema.json",
    "skill-lock.yaml": "lock.schema.json",
}
_CANONICAL_SOURCE_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
_CANONICAL_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"unhashable mapping key: {key!r}",
                key_node.start_mark,
            ) from error
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"duplicate mapping key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _schema_text(schema_name: str) -> str:
    repository_schema = Path(__file__).parents[2] / "schemas" / schema_name
    if repository_schema.is_file():
        return repository_schema.read_text(encoding="utf-8")
    packaged_schema = files("skill_delegator").joinpath("schemas", schema_name)
    return packaged_schema.read_text(encoding="utf-8")


def _load_document(config_dir: Path, filename: str, schema_name: str) -> dict[str, Any]:
    path = config_dir / filename
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise ConfigError(f"{filename}: invalid UTF-8: {error}") from error
    except OSError as error:
        raise ConfigError(f"{filename}: cannot read file: {error}") from error
    try:
        document = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as error:
        raise ConfigError(f"{filename}: invalid YAML: {error}") from error

    schema = json.loads(_schema_text(schema_name))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ConfigError(f"{filename} at {location}: {error.message}")
    return document


def _ensure_unique_ids(items: list[dict[str, Any]], kind: str) -> None:
    seen: set[str] = set()
    for item in items:
        identifier = item["id"]
        if identifier in seen:
            raise ConfigError(f"duplicate {kind} id: {identifier}")
        seen.add(identifier)


def _validate_path_string(value: str, filename: str, field: str) -> None:
    if "\0" in value:
        raise ConfigError(f"{filename} at {field}: path must not contain NUL")
    if any("\ud800" <= character <= "\udfff" for character in value):
        raise ConfigError(f"{filename} at {field}: path must not contain Unicode surrogates")
    try:
        os.fsencode(value)
    except UnicodeError as error:
        raise ConfigError(
            f"{filename} at {field}: path is not representable in the filesystem encoding"
        ) from error


def _resolve(config_dir: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = config_dir / path
    return path.resolve(strict=False)


def _validate_canonical_ids(values: list[str], filename: str) -> None:
    for value in values:
        parts = value.split("/")
        valid = (
            len(parts) >= 2
            and _CANONICAL_SOURCE_PATTERN.fullmatch(parts[0]) is not None
            and all(
                part not in {"", ".", ".."}
                and _CANONICAL_SEGMENT_PATTERN.fullmatch(part) is not None
                for part in parts[1:]
            )
        )
        if not valid:
            raise ConfigError(f"{filename}: invalid canonical skill id: {value!r}")


def _lexical_absolute(base: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return Path(os.path.abspath(path))


def _reject_symlink_components(repository_root: Path, target_root: Path) -> None:
    current = repository_root
    for part in target_root.relative_to(repository_root).parts:
        current /= part
        if current.is_symlink():
            raise ConfigError(f"main example target path must not contain symlinks: {current}")


def load_config(config_dir: Path, *, require_lock: bool = True) -> AuthorityConfig:
    """Load and validate one authority without reading source or target contents."""

    config_dir = config_dir.resolve(strict=False)
    documents = {
        filename: _load_document(config_dir, filename, schema)
        for filename, schema in _CONFIG_SCHEMAS.items()
        if require_lock or filename != "skill-lock.yaml"
    }
    authority = documents["authority.yaml"]["authority"]
    source_entries = documents["sources.yaml"]["sources"]
    pool_entries = documents["pool.yaml"]["skills"]
    target_entries = documents["delegations.yaml"]["targets"]

    for index, entry in enumerate(source_entries):
        for field in ("location", "skill_root"):
            _validate_path_string(entry[field], "sources.yaml", f"sources.{index}.{field}")
    for index, entry in enumerate(target_entries):
        _validate_path_string(entry["root"], "delegations.yaml", f"targets.{index}.root")

    _ensure_unique_ids(source_entries, "source")
    _ensure_unique_ids(target_entries, "target")

    _validate_canonical_ids(pool_entries, "pool.yaml")
    for target in target_entries:
        _validate_canonical_ids(target["grants"], "delegations.yaml")

    source_ids = {entry["id"] for entry in source_entries}
    for canonical_id in pool_entries:
        source_id = canonical_id.split("/", 1)[0]
        if source_id not in source_ids:
            raise ConfigError(f"pool.yaml: unknown source id in pool entry: {canonical_id}")

    pool = set(pool_entries)
    for target in target_entries:
        unknown = set(target["grants"]) - pool
        if unknown:
            raise ConfigError(
                f"delegations.yaml: target {target['id']} grants skills outside pool: "
                f"{', '.join(sorted(unknown))}"
            )

    fixture_policy = authority["fixture_policy"]
    if authority["id"] == "main-example" and fixture_policy != "safe-main-example":
        raise ConfigError("authority.yaml: main-example requires safe-main-example fixture policy")
    if fixture_policy == "safe-main-example":
        repository_root = config_dir.parent
        safe_parent = _lexical_absolute(repository_root, "var/example-targets")
        for target in target_entries:
            raw_root = Path(target["root"])
            if raw_root.is_absolute():
                raise ConfigError("main example target roots must be relative")
            lexical_root = _lexical_absolute(config_dir, raw_root)
            if not lexical_root.is_relative_to(safe_parent):
                raise ConfigError(
                    "main example target roots must resolve under var/example-targets/"
                )
            _reject_symlink_components(repository_root, lexical_root)

    sources = tuple(
        SourceSpec(
            id=entry["id"],
            type=entry["type"],
            location=(
                _resolve(config_dir, entry["location"])
                if entry["type"] == "filesystem"
                else entry["location"]
            ),
            skill_root=PurePosixPath(entry["skill_root"]),
            track=entry.get("track"),
        )
        for entry in source_entries
    )
    targets = tuple(
        TargetSpec(
            id=entry["id"],
            root=_resolve(config_dir, entry["root"]),
            grants=tuple(entry["grants"]),
        )
        for entry in target_entries
    )
    return AuthorityConfig(
        authority_id=authority["id"],
        fail_closed=authority["fail_closed"],
        fixture_policy=fixture_policy,
        sources=sources,
        pool=tuple(PoolSpec(canonical_id=value) for value in pool_entries),
        targets=targets,
    )
