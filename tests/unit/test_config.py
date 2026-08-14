from __future__ import annotations

import shutil
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from skill_delegator.config import load_config
from skill_delegator.errors import ConfigError

REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "config"
CONFIG_FILENAMES = (
    "authority.yaml",
    "sources.yaml",
    "pool.yaml",
    "delegations.yaml",
    "skill-lock.yaml",
)


def copy_config(tmp_path: Path) -> Path:
    destination = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, destination)
    return destination


def rewrite_yaml(config_dir: Path, filename: str, mutate: object) -> None:
    path = config_dir / filename
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_main_example_parses_with_safe_resolved_target_roots() -> None:
    config = load_config(EXAMPLE_CONFIG)

    assert config.authority_id == "main-example"
    assert len(config.sources) == 1
    assert len(config.pool) == 1
    assert len(config.targets) == 2
    expected_parent = (REPOSITORY_ROOT / "var" / "example-targets").resolve()
    assert all(target.root.is_relative_to(expected_parent) for target in config.targets)
    assert (
        config.sources[0].location
        == (REPOSITORY_ROOT / "tests" / "fixtures" / "example-source").resolve()
    )
    with pytest.raises(FrozenInstanceError):
        config.authority_id = "changed"  # type: ignore[misc]


def test_unknown_yaml_key_fails(tmp_path: Path) -> None:
    config_dir = copy_config(tmp_path)
    rewrite_yaml(
        config_dir,
        "authority.yaml",
        lambda document: document.update({"unexpected": True}),
    )

    with pytest.raises(ConfigError, match=r"authority\.yaml.*unexpected"):
        load_config(config_dir)


@pytest.mark.parametrize(
    ("filename", "collection"),
    (("sources.yaml", "sources"), ("delegations.yaml", "targets")),
)
def test_duplicate_ids_fail(tmp_path: Path, filename: str, collection: str) -> None:
    config_dir = copy_config(tmp_path)

    def duplicate(document: dict[str, object]) -> None:
        entries = document[collection]
        assert isinstance(entries, list)
        entries.append(dict(entries[0]))

    rewrite_yaml(config_dir, filename, duplicate)

    with pytest.raises(ConfigError, match=rf"duplicate {collection[:-1]} id"):
        load_config(config_dir)


def test_absolute_main_example_target_fails_fixture_policy(tmp_path: Path) -> None:
    config_dir = copy_config(tmp_path)

    def make_absolute(document: dict[str, object]) -> None:
        targets = document["targets"]
        assert isinstance(targets, list)
        targets[0]["root"] = str(tmp_path / "unsafe")

    rewrite_yaml(config_dir, "delegations.yaml", make_absolute)

    with pytest.raises(ConfigError, match="main example target roots must be relative"):
        load_config(config_dir)


@pytest.mark.parametrize("bad_grants", ["example/hello", [], ["invalid grant"]])
def test_malformed_grants_fail(tmp_path: Path, bad_grants: object) -> None:
    config_dir = copy_config(tmp_path)

    def replace_grants(document: dict[str, object]) -> None:
        targets = document["targets"]
        assert isinstance(targets, list)
        targets[0]["grants"] = bad_grants

    rewrite_yaml(config_dir, "delegations.yaml", replace_grants)

    with pytest.raises(ConfigError, match=r"delegations\.yaml"):
        load_config(config_dir)


@pytest.mark.parametrize("filename", ("pool.yaml", "delegations.yaml"))
@pytest.mark.parametrize(
    "bad_canonical_id",
    (
        "",
        ".",
        "..",
        "example/",
        "example/a/",
        "example/a//b",
        "example/a/./b",
        "example/a/../b",
        "example/a/../../outside",
    ),
)
def test_canonical_skill_ids_reject_malformed_path_segments(
    tmp_path: Path, filename: str, bad_canonical_id: str
) -> None:
    config_dir = copy_config(tmp_path)

    def replace_canonical_id(document: dict[str, object]) -> None:
        if filename == "pool.yaml":
            document["skills"] = [bad_canonical_id]
        else:
            targets = document["targets"]
            assert isinstance(targets, list)
            targets[0]["grants"] = [bad_canonical_id]

    rewrite_yaml(config_dir, filename, replace_canonical_id)

    with pytest.raises(
        ConfigError,
        match=rf"{filename.replace('.', r'\.')}: invalid canonical skill id",
    ):
        load_config(config_dir)


@pytest.mark.parametrize("symlink_component", ("example-targets", "worker"))
def test_main_example_rejects_existing_symlink_in_target_path(
    tmp_path: Path, symlink_component: str
) -> None:
    config_dir = copy_config(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    safe_parent_parent = tmp_path / "var"
    safe_parent_parent.mkdir()

    if symlink_component == "example-targets":
        (safe_parent_parent / "example-targets").symlink_to(outside, target_is_directory=True)
    else:
        safe_parent = safe_parent_parent / "example-targets"
        safe_parent.mkdir()
        (safe_parent / "worker").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ConfigError, match=r"target path must not contain symlinks"):
        load_config(config_dir)


@pytest.mark.parametrize("filename", CONFIG_FILENAMES)
def test_invalid_utf8_is_filename_bearing_config_error(tmp_path: Path, filename: str) -> None:
    config_dir = copy_config(tmp_path)
    (config_dir / filename).write_bytes(b"\xff")

    with pytest.raises(ConfigError, match=rf"{filename.replace('.', r'\.')}.*invalid UTF-8"):
        load_config(config_dir)


@pytest.mark.parametrize(
    ("filename", "content"),
    (
        ("authority.yaml", "schema_version: 1\nschema_version: 1\n"),
        (
            "delegations.yaml",
            "schema_version: 1\ntargets:\n  - id: worker\n    id: duplicate\n",
        ),
    ),
)
def test_duplicate_yaml_mapping_keys_fail_at_any_depth(
    tmp_path: Path, filename: str, content: str
) -> None:
    config_dir = copy_config(tmp_path)
    (config_dir / filename).write_text(content, encoding="utf-8")

    with pytest.raises(
        ConfigError,
        match=rf"{filename.replace('.', r'\.')}: invalid YAML:.*duplicate mapping key",
    ):
        load_config(config_dir)


def test_unhashable_yaml_mapping_key_is_filename_bearing_config_error(tmp_path: Path) -> None:
    config_dir = copy_config(tmp_path)
    (config_dir / "authority.yaml").write_text("? [a, b]\n: c\n", encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    message = str(exc_info.value)
    assert message.startswith("authority.yaml: invalid YAML:")
    assert "unhashable mapping key" in message
