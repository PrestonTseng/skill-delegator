"""Strict YAML and JSON Schema configuration loader."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

from skill_delegator.config_snapshot import (
    ConfigInput,
    ConfigInputSnapshot,
    assert_snapshot_current,
    input_from_open_file,
)
from skill_delegator.errors import ConfigError
from skill_delegator.identifiers import is_canonical_id, is_source_id
from skill_delegator.models import AuthorityConfig, PoolSpec, SourceSpec, TargetSpec
from skill_delegator.schema_validation import schema_error_location, schema_errors, schema_text

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


def _parse_document_bytes(
    data: bytes,
    filename: str,
    validation_errors: Callable[[Any], tuple[ValidationError, ...]],
) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as error:
        raise ConfigError(f"{filename}: invalid UTF-8: {error}") from error
    try:
        document = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as error:
        raise ConfigError(f"{filename}: invalid YAML: {error}") from error

    errors = validation_errors(document)
    if errors:
        error = errors[0]
        location = schema_error_location(error)
        raise ConfigError(f"{filename} at {location}: {error.message}")
    return document


def _load_document(data: bytes, filename: str, schema_name: str) -> dict[str, Any]:
    return _parse_document_bytes(
        data, filename, lambda document: schema_errors(document, schema_name)
    )


def _target_schema_errors(document: Any) -> tuple[Any, ...]:
    """Validate the singular schema with its sibling schema registered locally."""

    schema = json.loads(schema_text("target-delegation.schema.json"))
    legacy_schema = json.loads(schema_text("delegations.schema.json"))
    registry = Registry().with_resource(
        "delegations.schema.json", Resource.from_contents(legacy_schema)
    )
    return tuple(
        sorted(
            Draft202012Validator(schema, registry=registry).iter_errors(document),
            key=lambda error: (
                tuple(str(part) for part in error.absolute_path),
                tuple(str(part) for part in error.absolute_schema_path),
                str(error.validator),
            ),
        )
    )


_FILE_OPEN_FLAGS = (
    os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
)
_DIRECTORY_OPEN_FLAGS = _FILE_OPEN_FLAGS | os.O_DIRECTORY


def _identity(file_stat: os.stat_result) -> tuple[int, int]:
    return file_stat.st_dev, file_stat.st_ino


def _entry_identity(file_stat: os.stat_result) -> tuple[int, int, int]:
    return file_stat.st_dev, file_stat.st_ino, stat.S_IFMT(file_stat.st_mode)


def _optional_lstat(name: str, directory_fd: int) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _read_verified_file(
    directory_fd: int,
    basename: str,
    filename: str,
    discovered_stat: os.stat_result,
    *,
    captured_out: list[ConfigInput] | None = None,
) -> bytes:
    try:
        file_fd = os.open(basename, _FILE_OPEN_FLAGS, dir_fd=directory_fd)
    except OSError as error:
        raise ConfigError(f"{filename}: cannot open no-follow file: {error}") from error
    try:
        opened_stat = os.fstat(file_fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ConfigError(f"{filename}: delegation input must be a regular file")
        if _identity(opened_stat) != _identity(discovered_stat):
            raise ConfigError(f"{filename}: delegation file changed after discovery")
        parent_stat = os.fstat(directory_fd)
        with os.fdopen(file_fd, "rb") as stream:
            file_fd = -1
            data = stream.read()
        if len(data) != opened_stat.st_size:
            raise ConfigError(f"{filename}: delegation file changed while reading")
        if captured_out is not None:
            captured_out.append(input_from_open_file(filename, data, parent_stat, opened_stat))
        return data
    except OSError as error:
        raise ConfigError(f"{filename}: cannot read file: {error}") from error
    finally:
        if file_fd >= 0:
            os.close(file_fd)


def _directory_entries(directory_fd: int) -> dict[str, os.stat_result]:
    try:
        enumeration_fd = os.open(".", _DIRECTORY_OPEN_FLAGS, dir_fd=directory_fd)
    except OSError as error:
        raise ConfigError(
            f"delegations/: cannot open directory for fresh enumeration: {error}"
        ) from error
    try:
        try:
            names = sorted(os.listdir(enumeration_fd), key=os.fsencode)
        except OSError as error:
            raise ConfigError(f"delegations/: cannot read directory: {error}") from error
        if not names:
            raise ConfigError("delegations/: delegation directory must not be empty")

        entries: dict[str, os.stat_result] = {}
        for name in names:
            filename = f"delegations/{name}"
            try:
                entry_stat = os.stat(name, dir_fd=enumeration_fd, follow_symlinks=False)
            except OSError as error:
                raise ConfigError(f"{filename}: cannot inspect entry: {error}") from error
            if stat.S_ISLNK(entry_stat.st_mode):
                raise ConfigError(f"{filename}: delegation entry must not be a symlink")
            if not stat.S_ISREG(entry_stat.st_mode):
                raise ConfigError(f"{filename}: delegation entry must be a regular YAML file")
            if not name.endswith(".yaml"):
                raise ConfigError(f"{filename}: delegation filename must end in .yaml")
            stem = name.removesuffix(".yaml")
            if not is_source_id(stem):
                raise ConfigError(f"{filename}: unsafe delegation filename")
            entries[name] = entry_stat
        return entries
    finally:
        os.close(enumeration_fd)


@dataclass
class _DelegationInputs:
    mode: str
    names: tuple[str, ...]
    config_fd: int
    discovered: dict[str, os.stat_result]
    directory_fd: int | None = None
    captured: tuple[ConfigInput, ...] = ()

    def close(self) -> None:
        if self.directory_fd is not None:
            os.close(self.directory_fd)
            self.directory_fd = None
        if self.config_fd >= 0:
            os.close(self.config_fd)
            self.config_fd = -1

    def load_documents(self) -> tuple[dict[str, Any], ...]:
        captured: list[ConfigInput] = []
        if self.mode == "single":
            discovered_stat = self.discovered["delegations.yaml"]
            data = _read_verified_file(
                self.config_fd,
                "delegations.yaml",
                "delegations.yaml",
                discovered_stat,
            )
            captured.append(
                input_from_open_file(
                    "delegations.yaml", data, os.fstat(self.config_fd), discovered_stat
                )
            )
            current_stat = _optional_lstat("delegations.yaml", self.config_fd)
            if current_stat is None or _identity(current_stat) != _identity(discovered_stat):
                raise ConfigError("delegations.yaml: delegation file changed while reading")
            self.captured = tuple(captured)
            return (
                _parse_document_bytes(
                    data,
                    "delegations.yaml",
                    lambda document: schema_errors(document, "delegations.schema.json"),
                ),
            )

        assert self.directory_fd is not None
        documents = []
        for filename in self.names:
            basename = filename.removeprefix("delegations/")
            data = _read_verified_file(
                self.directory_fd,
                basename,
                filename,
                self.discovered[basename],
            )
            captured.append(
                input_from_open_file(
                    filename,
                    data,
                    os.fstat(self.directory_fd),
                    self.discovered[basename],
                )
            )
            documents.append(_parse_document_bytes(data, filename, _target_schema_errors))

        current = _directory_entries(self.directory_fd)
        if tuple(current) != tuple(self.discovered) or any(
            _entry_identity(current[name]) != _entry_identity(discovered_stat)
            for name, discovered_stat in self.discovered.items()
        ):
            raise ConfigError("delegations/: delegation entry set changed while reading")
        self.captured = tuple(captured)
        return tuple(documents)


def _delegation_input_names(config_dir: Path) -> _DelegationInputs:
    """Discover exactly one delegation form without following symlinks."""

    try:
        config_fd = os.open(config_dir, _DIRECTORY_OPEN_FLAGS)
    except OSError as error:
        raise ConfigError(
            f"cannot open configuration directory without following symlinks: {error}"
        ) from error

    directory_fd: int | None = None
    try:
        legacy_stat = _optional_lstat("delegations.yaml", config_fd)
        directory_stat = _optional_lstat("delegations", config_fd)
        legacy_exists = legacy_stat is not None
        directory_exists = directory_stat is not None

        if legacy_exists and directory_exists:
            raise ConfigError("delegations.yaml and delegations/ cannot both be present")
        if not legacy_exists and not directory_exists:
            raise ConfigError("delegations.yaml or delegations/ must be present")

        if legacy_stat is not None:
            if stat.S_ISLNK(legacy_stat.st_mode):
                raise ConfigError("delegations.yaml: delegation file must not be a symlink")
            if not stat.S_ISREG(legacy_stat.st_mode):
                raise ConfigError("delegations.yaml: delegation input must be a regular file")
            return _DelegationInputs(
                "single", ("delegations.yaml",), config_fd, {"delegations.yaml": legacy_stat}
            )

        assert directory_stat is not None
        if stat.S_ISLNK(directory_stat.st_mode):
            raise ConfigError("delegations/: delegation directory must not be a symlink")
        if not stat.S_ISDIR(directory_stat.st_mode):
            raise ConfigError("delegations/: delegation input must be a directory")

        try:
            directory_fd = os.open("delegations", _DIRECTORY_OPEN_FLAGS, dir_fd=config_fd)
        except OSError as error:
            raise ConfigError(f"delegations/: cannot open no-follow directory: {error}") from error
        opened_stat = os.fstat(directory_fd)
        if not stat.S_ISDIR(opened_stat.st_mode):
            raise ConfigError("delegations/: delegation input must be a directory")
        if _identity(opened_stat) != _identity(directory_stat):
            raise ConfigError("delegations/: delegation directory changed after discovery")

        entries = _directory_entries(directory_fd)
        names = tuple(f"delegations/{name}" for name in entries)
        return _DelegationInputs("multiple", names, config_fd, entries, directory_fd)
    except BaseException:
        if directory_fd is not None:
            os.close(directory_fd)
        os.close(config_fd)
        raise


def config_input_names(config_dir: Path) -> tuple[str, ...]:
    """Return deterministic POSIX-relative names of desired-state inputs."""

    config_dir = config_dir.resolve(strict=False)
    delegation_inputs = _delegation_input_names(config_dir)
    try:
        common = tuple(name for name in _CONFIG_SCHEMAS if name != "delegations.yaml")
        return tuple(sorted((*common, *delegation_inputs.names), key=os.fsencode))
    finally:
        delegation_inputs.close()


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


def load_config(
    config_dir: Path, *, require_lock: bool = True, target_scope: str | None = None
) -> AuthorityConfig:
    """Load and validate one authority without reading source or target contents."""

    config_dir = config_dir.resolve(strict=False)
    delegation_inputs = _delegation_input_names(config_dir)
    try:
        common_inputs: list[ConfigInput] = []
        common_bytes: dict[str, bytes] = {}
        for filename in _CONFIG_SCHEMAS:
            if filename == "delegations.yaml" or (
                not require_lock and filename == "skill-lock.yaml"
            ):
                continue
            discovered_stat = _optional_lstat(filename, delegation_inputs.config_fd)
            if discovered_stat is None:
                raise ConfigError(f"{filename}: cannot read file: file does not exist")
            if stat.S_ISLNK(discovered_stat.st_mode) or not stat.S_ISREG(discovered_stat.st_mode):
                raise ConfigError(f"{filename}: configuration input must be a regular file")
            data = _read_verified_file(
                delegation_inputs.config_fd, filename, filename, discovered_stat
            )
            common_bytes[filename] = data
            common_inputs.append(
                input_from_open_file(
                    filename,
                    data,
                    os.fstat(delegation_inputs.config_fd),
                    discovered_stat,
                )
            )
        documents = {
            filename: _load_document(common_bytes[filename], filename, schema)
            for filename, schema in _CONFIG_SCHEMAS.items()
            if filename != "delegations.yaml"
            if require_lock or filename != "skill-lock.yaml"
        }
        delegation_documents = delegation_inputs.load_documents()
        config_stat = os.fstat(delegation_inputs.config_fd)
        snapshot = ConfigInputSnapshot(
            config_dir,
            (config_stat.st_dev, config_stat.st_ino),
            tuple(
                sorted(
                    (*common_inputs, *delegation_inputs.captured),
                    key=lambda item: os.fsencode(item.name),
                )
            ),
        )
    finally:
        delegation_inputs.close()

    try:
        assert_snapshot_current(snapshot)
    except ValueError as error:
        raise ConfigError("configuration snapshot changed") from error

    delegation_mode = delegation_inputs.mode
    delegation_names = delegation_inputs.names
    if delegation_mode == "single":
        delegation_document = delegation_documents[0]
        target_records = [
            (entry, "delegations.yaml", "shared") for entry in delegation_document["targets"]
        ]
    else:
        target_records = []
        for filename, document in zip(delegation_names, delegation_documents, strict=True):
            entry = document["target"]
            target_records.append((entry, filename, filename))

    authority = documents["authority.yaml"]["authority"]
    source_entries = documents["sources.yaml"]["sources"]
    pool_entries = documents["pool.yaml"]["skills"]

    for index, entry in enumerate(source_entries):
        for field in ("location", "skill_root"):
            _validate_path_string(entry[field], "sources.yaml", f"sources.{index}.{field}")
    for index, (entry, filename, _) in enumerate(target_records):
        field = f"targets.{index}.root" if delegation_mode == "single" else "target.root"
        _validate_path_string(entry["root"], filename, field)
    if "skill-lock.yaml" in documents:
        for source_index, locked_source in enumerate(documents["skill-lock.yaml"]["sources"]):
            for skill_index, locked_skill in enumerate(locked_source["skills"]):
                _validate_path_string(
                    locked_skill["path"],
                    "skill-lock.yaml",
                    f"sources.{source_index}.skills.{skill_index}.path",
                )

    _ensure_unique_ids(source_entries, "source")
    seen_target_ids: set[str] = set()
    for entry, filename, _ in target_records:
        if entry["id"] in seen_target_ids:
            raise ConfigError(f"{filename}: duplicate target id: {entry['id']}")
        seen_target_ids.add(entry["id"])
    if delegation_mode == "multiple":
        for entry, filename, _ in target_records:
            expected_id = Path(filename).stem
            if entry["id"] != expected_id:
                raise ConfigError(
                    f"{filename}: target id {entry['id']!r} must match filename stem "
                    f"{expected_id!r}"
                )

    _validate_canonical_ids(pool_entries, "pool.yaml")
    for target, filename, _ in target_records:
        _validate_canonical_ids(target["grants"], filename)

    source_ids = {entry["id"] for entry in source_entries}
    for canonical_id in pool_entries:
        source_id = canonical_id.split("/", 1)[0]
        if source_id not in source_ids:
            raise ConfigError(f"pool.yaml: unknown source id in pool entry: {canonical_id}")

    pool = set(pool_entries)
    for target, filename, _ in target_records:
        unknown = set(target["grants"]) - pool
        if unknown:
            raise ConfigError(
                f"{filename}: target {target['id']} grants skills outside pool: "
                f"{', '.join(sorted(unknown))}"
            )

    fixture_policy = authority["fixture_policy"]
    if authority["id"] == "main-example" and fixture_policy != "safe-main-example":
        raise ConfigError("authority.yaml: main-example requires safe-main-example fixture policy")
    if fixture_policy == "safe-main-example":
        repository_root = config_dir.parent
        safe_parent = _lexical_absolute(repository_root, "var/example-targets")
        for target, filename, _ in target_records:
            raw_root = Path(target["root"])
            if raw_root.is_absolute():
                raise ConfigError(f"{filename}: main example target roots must be relative")
            lexical_root = _lexical_absolute(config_dir, raw_root)
            if not lexical_root.is_relative_to(safe_parent):
                raise ConfigError(
                    f"{filename}: main example target roots must resolve under var/example-targets/"
                )
            if target_scope is None or target["id"] == target_scope:
                try:
                    _reject_symlink_components(repository_root, lexical_root)
                except ConfigError as error:
                    raise ConfigError(f"{filename}: {error}") from error

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
            deployment_scope=deployment_scope,
        )
        for entry, _, deployment_scope in sorted(target_records, key=lambda record: record[0]["id"])
    )
    return AuthorityConfig(
        authority_id=authority["id"],
        fail_closed=authority["fail_closed"],
        fixture_policy=fixture_policy,
        sources=sources,
        pool=tuple(PoolSpec(canonical_id=value) for value in pool_entries),
        targets=targets,
        cache_root=config_dir.parent / "var" / "cache" / "sources",
        delegation_mode=delegation_mode,
        input_snapshot=snapshot,
    )
