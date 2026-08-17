"""Strict YAML and JSON Schema configuration loader."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from skill_delegator.errors import ConfigError
from skill_delegator.identifiers import is_canonical_id
from skill_delegator.models import AuthorityConfig, PoolSpec, SourceSpec, TargetSpec
from skill_delegator.schema_validation import schema_error_location, schema_errors

_CONFIG_SCHEMAS = {
    "authority.yaml": "authority.schema.json",
    "sources.yaml": "sources.schema.json",
    "pool.yaml": "pool.schema.json",
    "delegations.yaml": "delegations.schema.json",
    "skill-lock.yaml": "lock.schema.json",
}


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

    errors = schema_errors(document, schema_name)
    if errors:
        error = errors[0]
        location = schema_error_location(error)
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
    # Preserve the lexical chain so source validation can reject symlinked
    # ancestors instead of silently converting them to an external real path.
    return Path(os.path.abspath(path))


def _validate_canonical_ids(values: list[str], filename: str) -> None:
    for value in values:
        if not is_canonical_id(value):
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
        if os.path.lexists(current) and not current.is_dir():
            raise ConfigError(f"main example target path component must be a directory: {current}")


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
    if "skill-lock.yaml" in documents:
        for source_index, locked_source in enumerate(documents["skill-lock.yaml"]["sources"]):
            for skill_index, locked_skill in enumerate(locked_source["skills"]):
                _validate_path_string(
                    locked_skill["path"],
                    "skill-lock.yaml",
                    f"sources.{source_index}.skills.{skill_index}.path",
                )

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
            root=_lexical_absolute(config_dir, entry["root"]),
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
        cache_root=config_dir.parent / "var" / "cache" / "sources",
    )
