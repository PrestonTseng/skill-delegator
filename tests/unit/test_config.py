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
