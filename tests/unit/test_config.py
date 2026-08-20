from __future__ import annotations

import json
import os
import shutil
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from skill_delegator import config as config_module
from skill_delegator.config import load_config
from skill_delegator.errors import ConfigError
from skill_delegator.schema_validation import schema_text

REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "config"
CONFIG_FILENAMES = (
    "authority.yaml",
    "sources.yaml",
    "pool.yaml",
    "delegations.yaml",
    "skill-lock.yaml",
)
PATH_FIELDS = (
    ("sources.yaml", "sources", "location"),
    ("sources.yaml", "sources", "skill_root"),
    ("delegations.yaml", "targets", "root"),
)


def lock_document(
    path: str = "banner-design", canonical_id: str = "source/banner-design"
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sources": [
            {
                "source_id": "source",
                "type": "filesystem",
                "tree_hash": "a" * 64,
                "skills": [
                    {
                        "canonical_id": canonical_id,
                        "runtime_name": "banner-design",
                        "path": path,
                        "sha256": "b" * 64,
                    }
                ],
            }
        ],
    }


def copy_config(tmp_path: Path) -> Path:
    destination = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, destination)
    return destination


def rewrite_yaml(config_dir: Path, filename: str, mutate: object) -> None:
    path = config_dir / filename
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def write_yaml(path: Path, document: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def use_per_target_delegations(config_dir: Path) -> Path:
    (config_dir / "delegations.yaml").unlink()
    rewrite_yaml(
        config_dir,
        "authority.yaml",
        lambda document: document["authority"].update(
            {"id": "non-fixture", "fixture_policy": "none"}
        ),
    )
    delegations = config_dir / "delegations"
    delegations.mkdir()
    return delegations


def target_document(target_id: str, *, grants: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": {
            "id": target_id,
            "root": f"../targets/{target_id}",
            "grants": grants or ["example/hello"],
        },
    }


def test_per_target_delegation_document_loads_with_scope_mode_and_inputs(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "worker.yaml", target_document("worker"))

    loaded = load_config(config)

    assert loaded.delegation_mode == "multiple"
    assert loaded.targets[0].deployment_scope == "delegations/worker.yaml"
    assert config_module.config_input_names(config) == (
        "authority.yaml",
        "delegations/worker.yaml",
        "pool.yaml",
        "skill-lock.yaml",
        "sources.yaml",
    )


def test_legacy_delegations_use_shared_scope_and_single_mode() -> None:
    loaded = load_config(EXAMPLE_CONFIG)

    assert loaded.delegation_mode == "single"
    assert all(target.deployment_scope == "shared" for target in loaded.targets)
    assert config_module.config_input_names(EXAMPLE_CONFIG) == tuple(sorted(CONFIG_FILENAMES))


def test_per_target_files_are_discovered_in_filesystem_byte_order(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "zeta.yaml", target_document("zeta"))
    write_yaml(delegations / "alpha.yaml", target_document("alpha"))

    assert config_module.config_input_names(config) == (
        "authority.yaml",
        "delegations/alpha.yaml",
        "delegations/zeta.yaml",
        "pool.yaml",
        "skill-lock.yaml",
        "sources.yaml",
    )
    assert tuple(target.id for target in load_config(config).targets) == ("alpha", "zeta")


def test_per_target_filename_stem_must_match_target_id(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "worker.yaml", target_document("other"))

    with pytest.raises(ConfigError, match=r"delegations/worker\.yaml.*other"):
        load_config(config)


def test_duplicate_ids_across_per_target_files_are_filename_bearing(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "first.yaml", target_document("duplicate"))
    write_yaml(delegations / "second.yaml", target_document("duplicate"))

    with pytest.raises(ConfigError, match=r"delegations/second\.yaml.*duplicate target id"):
        load_config(config)


def test_legacy_and_per_target_forms_cannot_both_be_present(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = config / "delegations"
    delegations.mkdir()
    write_yaml(delegations / "worker.yaml", target_document("worker"))

    with pytest.raises(ConfigError, match=r"delegations\.yaml.*delegations/"):
        load_config(config)


def test_per_target_directory_cannot_be_empty(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    use_per_target_delegations(config)

    with pytest.raises(ConfigError, match=r"delegations/.*empty"):
        load_config(config)


@pytest.mark.parametrize("entry_name", ("nested", "worker.txt"))
def test_per_target_directory_rejects_nested_or_non_yaml_entries(
    tmp_path: Path, entry_name: str
) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    entry = delegations / entry_name
    if entry.suffix:
        entry.write_text("not a delegation", encoding="utf-8")
    else:
        entry.mkdir()

    with pytest.raises(ConfigError, match=rf"delegations/{entry_name.replace('.', r'\.')}"):
        load_config(config)


def test_per_target_directory_rejects_symlinked_file(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    outside = tmp_path / "outside.yaml"
    write_yaml(outside, target_document("worker"))
    (delegations / "worker.yaml").symlink_to(outside)

    with pytest.raises(ConfigError, match=r"delegations/worker\.yaml.*symlink"):
        load_config(config)


def test_per_target_directory_itself_cannot_be_a_symlink(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    (config / "delegations.yaml").unlink()
    outside = tmp_path / "outside"
    outside.mkdir()
    write_yaml(outside / "worker.yaml", target_document("worker"))
    (config / "delegations").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ConfigError, match=r"delegations/.*symlink"):
        load_config(config)


def test_per_target_regular_file_is_read_from_discovered_directory(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "worker.yaml", target_document("worker"))

    loaded = load_config(config)

    assert loaded.targets[0].id == "worker"
    assert loaded.targets[0].root == tmp_path / "targets" / "worker"


def test_per_target_directory_replacement_after_discovery_cannot_substitute_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "worker.yaml", target_document("worker"))
    outside = tmp_path / "outside-delegations"
    outside.mkdir()
    write_yaml(
        outside / "worker.yaml",
        {
            **target_document("worker"),
            "target": {
                **target_document("worker")["target"],
                "root": "../targets/substituted",
            },
        },
    )
    discovered = tmp_path / "discovered-delegations"
    real_discovery = config_module._delegation_input_names

    def replace_directory_after_discovery(config_dir: Path):
        result = real_discovery(config_dir)
        delegations.rename(discovered)
        delegations.symlink_to(outside, target_is_directory=True)
        return result

    monkeypatch.setattr(config_module, "_delegation_input_names", replace_directory_after_discovery)

    loaded = load_config(config)

    assert loaded.targets[0].root == tmp_path / "targets" / "worker"


def test_per_target_entry_added_after_read_changes_entry_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "worker.yaml", target_document("worker"))
    real_read = config_module._read_verified_file

    def add_entry_after_read(
        directory_fd: int,
        basename: str,
        filename: str,
        discovered_stat: os.stat_result,
    ) -> bytes:
        data = real_read(directory_fd, basename, filename, discovered_stat)
        write_yaml(delegations / "other.yaml", target_document("other"))
        return data

    monkeypatch.setattr(config_module, "_read_verified_file", add_entry_after_read)

    with pytest.raises(ConfigError, match=r"delegations/.*entry set changed"):
        load_config(config)


def test_per_target_invalid_utf8_is_filename_bearing(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    (delegations / "worker.yaml").write_bytes(b"\xff")

    with pytest.raises(ConfigError, match=r"delegations/worker\.yaml.*invalid UTF-8"):
        load_config(config)


def test_per_target_duplicate_yaml_keys_are_filename_bearing(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    (delegations / "worker.yaml").write_text(
        "schema_version: 1\ntarget:\n  id: worker\n  id: duplicate\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match=r"delegations/worker\.yaml: invalid YAML:.*duplicate"):
        load_config(config)


def test_per_target_directory_rejects_unsafe_filename(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(delegations / "Worker.yaml", target_document("worker"))

    with pytest.raises(ConfigError, match=r"delegations/Worker\.yaml.*filename"):
        load_config(config)


def test_per_target_grants_outside_pool_are_filename_bearing(tmp_path: Path) -> None:
    config = copy_config(tmp_path)
    delegations = use_per_target_delegations(config)
    write_yaml(
        delegations / "worker.yaml",
        target_document("worker", grants=["example/not-in-pool"]),
    )

    with pytest.raises(ConfigError, match=r"delegations/worker\.yaml.*outside pool"):
        load_config(config)


def test_main_example_parses_with_safe_lexical_target_roots() -> None:
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


def test_target_scope_checks_only_selected_safe_example_target_root(
    tmp_path: Path, monkeypatch
) -> None:
    config_dir = copy_config(tmp_path)
    checked: list[Path] = []
    monkeypatch.setattr(
        config_module,
        "_reject_symlink_components",
        lambda _repository_root, target_root: checked.append(target_root),
    )

    load_config(config_dir, target_scope="worker")

    assert checked == [tmp_path / "var" / "example-targets" / "worker"]


def test_non_fixture_target_root_preserves_symlink_ancestor_lexically(tmp_path: Path) -> None:
    config_dir = copy_config(tmp_path)
    rewrite_yaml(
        config_dir,
        "authority.yaml",
        lambda document: document["authority"].update(
            {"id": "non-fixture", "fixture_policy": "none"}
        ),
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    rewrite_yaml(
        config_dir,
        "delegations.yaml",
        lambda document: document["targets"][0].update({"root": "../linked/worker"}),
    )

    config = load_config(config_dir)

    worker = next(target for target in config.targets if target.id == "worker")
    assert worker.root == tmp_path / "linked" / "worker"
    assert worker.root != (tmp_path / "linked" / "worker").resolve()


def test_lock_generation_loader_mode_allows_missing_lock_but_validation_requires_it(
    tmp_path: Path,
) -> None:
    config_dir = copy_config(tmp_path)
    (config_dir / "skill-lock.yaml").unlink()

    config = load_config(config_dir, require_lock=False)

    assert config.authority_id == "main-example"
    with pytest.raises(ConfigError, match=r"skill-lock\.yaml: cannot read file"):
        load_config(config_dir)


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
        "example/.hidden",
        "example/a\\b",
        "example/a\nb",
        "example/a\x1fb",
        "example/é",
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
        match=rf"{filename.replace('.', r'\.')}(?: at .*(?:does not match|should not be valid)|: invalid canonical skill id)",
    ):
        load_config(config_dir)


@pytest.mark.parametrize(
    ("schema_name", "document", "bad_value"),
    (
        (
            "lock.schema.json",
            {
                "schema_version": 1,
                "sources": [
                    {
                        "source_id": "example",
                        "type": "filesystem",
                        "tree_hash": "a" * 64,
                        "skills": [
                            {
                                "canonical_id": "example/a",
                                "runtime_name": "a",
                                "path": "a",
                                "sha256": "b" * 64,
                            }
                        ],
                    }
                ],
            },
            "canonical_id",
        ),
        (
            "lock.schema.json",
            {
                "schema_version": 1,
                "sources": [
                    {
                        "source_id": "example",
                        "type": "filesystem",
                        "tree_hash": "a" * 64,
                        "skills": [
                            {
                                "canonical_id": "example/a",
                                "runtime_name": "a",
                                "path": "a",
                                "sha256": "b" * 64,
                            }
                        ],
                    }
                ],
            },
            "path",
        ),
        ("pool.schema.json", {"schema_version": 1, "skills": ["example/a"]}, "skills"),
        (
            "delegations.schema.json",
            {
                "schema_version": 1,
                "targets": [{"id": "worker", "root": "target", "grants": ["example/a"]}],
            },
            "grants",
        ),
    ),
)
@pytest.mark.parametrize("suffix", ("\n", "\r", "\x00", "\x1f", "\x7f"))
def test_canonical_json_schemas_directly_reject_trailing_ascii_controls(
    schema_name: str, document: dict[str, Any], bad_value: str, suffix: str
) -> None:
    candidate = json.loads(json.dumps(document))
    if schema_name == "lock.schema.json":
        skill = candidate["sources"][0]["skills"][0]
        skill[bad_value] += suffix
    elif bad_value == "skills":
        candidate["skills"][0] += suffix
    else:
        candidate["targets"][0]["grants"][0] += suffix

    errors = list(Draft202012Validator(json.loads(schema_text(schema_name))).iter_errors(candidate))

    assert errors


@pytest.mark.parametrize(
    "path",
    (
        ".claude/skills/banner-design",
        "skills/.internal/banner-design",
        "skills/banner-design.v1",
    ),
)
def test_lock_schema_accepts_safe_snapshot_relative_paths_with_hidden_segments(path: str) -> None:
    validator = Draft202012Validator(json.loads(schema_text("lock.schema.json")))

    assert list(validator.iter_errors(lock_document(path))) == []


@pytest.mark.parametrize(
    "path",
    (
        "/absolute/banner-design",
        "",
        "skills//banner-design",
        "skills/banner-design/",
        ".",
        "..",
        "skills/./banner-design",
        "skills/../banner-design",
        "skills\\banner-design",
        "skills/banner\x00design",
        "skills/banner\x1fdesign",
        "skills/banner\x7fdesign",
        "skills/banner\ud800design",
    ),
)
def test_lock_schema_rejects_unsafe_snapshot_relative_paths(path: str) -> None:
    validator = Draft202012Validator(json.loads(schema_text("lock.schema.json")))

    assert list(validator.iter_errors(lock_document(path)))


@pytest.mark.parametrize(
    "canonical_id",
    (
        "source/.claude/banner-design",
        "source/skills/.hidden",
        "source/banner\x00design",
        "source/banner\ud800design",
    ),
)
def test_hidden_lock_path_support_does_not_weaken_canonical_id_schema(
    canonical_id: str,
) -> None:
    validator = Draft202012Validator(json.loads(schema_text("lock.schema.json")))

    assert list(validator.iter_errors(lock_document(".claude/skills/banner-design", canonical_id)))


def test_loaded_lock_path_must_be_representable_in_filesystem_encoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = copy_config(tmp_path)
    rewrite_yaml(
        config_dir,
        "skill-lock.yaml",
        lambda document: document["sources"][0]["skills"][0].update(
            {"path": ".claude/skills/banner-design"}
        ),
    )
    real_fsencode = config_module.os.fsencode

    def reject_lock_path(value: str) -> bytes:
        if value == ".claude/skills/banner-design":
            raise UnicodeEncodeError("ascii", value, 0, 1, "injected")
        return real_fsencode(value)

    monkeypatch.setattr(config_module.os, "fsencode", reject_lock_path)

    with pytest.raises(ConfigError, match="skill-lock.*path.*filesystem encoding"):
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


@pytest.mark.parametrize("fixture_policy", ("safe-main-example", "none"))
@pytest.mark.parametrize(("filename", "collection", "field"), PATH_FIELDS)
def test_nul_in_path_field_is_filename_and_field_bearing_config_error(
    tmp_path: Path,
    fixture_policy: str,
    filename: str,
    collection: str,
    field: str,
) -> None:
    config_dir = copy_config(tmp_path)
    if fixture_policy == "none":
        rewrite_yaml(
            config_dir,
            "authority.yaml",
            lambda document: document["authority"].update(
                {"id": "non-fixture", "fixture_policy": "none"}
            ),
        )

    def inject_nul(document: dict[str, object]) -> None:
        entries = document[collection]
        assert isinstance(entries, list)
        entries[0][field] = "before\0after"

    rewrite_yaml(config_dir, filename, inject_nul)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    message = str(exc_info.value)
    assert message.startswith(f"{filename} at {collection}.0.{field}:")
    assert "NUL" in message


@pytest.mark.parametrize("fixture_policy", ("safe-main-example", "none"))
@pytest.mark.parametrize(("filename", "collection", "field"), PATH_FIELDS)
@pytest.mark.parametrize("surrogate_code_point", (0xD800, 0xDFFF), ids=("high", "low"))
def test_lone_surrogate_in_any_path_field_is_precise_config_error(
    tmp_path: Path,
    fixture_policy: str,
    filename: str,
    collection: str,
    field: str,
    surrogate_code_point: int,
) -> None:
    config_dir = copy_config(tmp_path)
    surrogate = chr(surrogate_code_point)
    if fixture_policy == "none":
        rewrite_yaml(
            config_dir,
            "authority.yaml",
            lambda document: document["authority"].update(
                {"id": "non-fixture", "fixture_policy": "none"}
            ),
        )

    def inject_surrogate(document: dict[str, object]) -> None:
        entries = document[collection]
        assert isinstance(entries, list)
        entries[0][field] = f"before{surrogate}after"

    rewrite_yaml(config_dir, filename, inject_surrogate)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    message = str(exc_info.value)
    assert message.startswith(f"{filename} at {collection}.0.{field}:")
    assert "surrogate" in message


@pytest.mark.parametrize(("filename", "collection", "field"), PATH_FIELDS)
def test_filesystem_unencodable_path_field_is_precise_config_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    collection: str,
    field: str,
) -> None:
    config_dir = copy_config(tmp_path)

    def inject_rejected_value(document: dict[str, object]) -> None:
        entries = document[collection]
        assert isinstance(entries, list)
        entries[0][field] = "filesystem-rejected"

    rewrite_yaml(config_dir, filename, inject_rejected_value)

    def reject_test_value(value: Any) -> bytes:
        if value == "filesystem-rejected":
            raise UnicodeEncodeError("test-filesystem", value, 0, 1, "cannot encode")
        return value.encode()

    monkeypatch.setattr("skill_delegator.config.os.fsencode", reject_test_value)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    message = str(exc_info.value)
    assert message.startswith(f"{filename} at {collection}.0.{field}:")
    assert "filesystem encoding" in message


def test_ordinary_unicode_is_preserved_in_all_path_fields(tmp_path: Path) -> None:
    config_dir = copy_config(tmp_path)
    rewrite_yaml(
        config_dir,
        "authority.yaml",
        lambda document: document["authority"].update(
            {"id": "non-fixture", "fixture_policy": "none"}
        ),
    )

    def use_unicode_source_paths(document: dict[str, object]) -> None:
        source = document["sources"][0]
        source["location"] = "../資料/技能"
        source["skill_root"] = "能力"

    rewrite_yaml(config_dir, "sources.yaml", use_unicode_source_paths)
    rewrite_yaml(
        config_dir,
        "delegations.yaml",
        lambda document: document["targets"][0].update({"root": "../輸出/目標"}),
    )

    config = load_config(config_dir)

    assert config.sources[0].location == (config_dir / "../資料/技能").resolve()
    assert config.sources[0].skill_root == Path("能力")
    worker = next(target for target in config.targets if target.id == "worker")
    assert worker.root == (config_dir / "../輸出/目標").resolve()


def test_git_location_remains_repository_string_while_filesystem_location_is_resolved(
    tmp_path: Path,
) -> None:
    filesystem_config = load_config(EXAMPLE_CONFIG)
    assert isinstance(filesystem_config.sources[0].location, Path)
    assert filesystem_config.sources[0].location.is_absolute()

    config_dir = copy_config(tmp_path)

    def use_git_source(document: dict[str, object]) -> None:
        sources = document["sources"]
        assert isinstance(sources, list)
        source = sources[0]
        assert isinstance(source, dict)
        source.update(
            {
                "type": "git",
                "location": "ssh://git@example.invalid/skills.git",
                "track": "main",
            }
        )

    rewrite_yaml(config_dir, "sources.yaml", use_git_source)
    git_config = load_config(config_dir)

    assert git_config.sources[0].location == "ssh://git@example.invalid/skills.git"
    assert isinstance(git_config.sources[0].location, str)
    assert git_config.sources[0].track == "main"
