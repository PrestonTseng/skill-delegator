from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest
import yaml

from skill_delegator.descriptor_tree import discover_skills_at, hash_tree_at
from skill_delegator.errors import SourceError
from skill_delegator.inventory import (
    _hash_record,
    _inventory_paths,
    discover_skills,
    hash_tree,
    validate_snapshot_tree,
)
from skill_delegator.lockfile import build_lock, serialize_lock
from skill_delegator.models import AuthorityConfig, SourceSpec
from skill_delegator.resolver import ResolutionError, resolve_desired_state
from skill_delegator.source_store import resolve_sources


def _write_skill(root: Path, relative: str, name: str = "demo") -> Path:
    directory = root / relative
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Portable hash fixture\n---\nbody\n",
        encoding="utf-8",
    )
    return directory


def _config(source: Path) -> AuthorityConfig:
    return AuthorityConfig(
        authority_id="test",
        fail_closed=True,
        fixture_policy="none",
        sources=(SourceSpec("local", "filesystem", source, PurePosixPath("skills")),),
        pool=(),
        targets=(),
    )


def _record(kind: bytes, mode: int) -> bytes:
    digest = hashlib.sha256()
    _hash_record(digest, kind, b"entry", mode, b"payload")
    return digest.digest()


def test_portable_modes_ignore_host_permissions_but_retain_executable_identity() -> None:
    assert _record(b"D", 0o700) == _record(b"D", 0o755)
    assert _record(b"L", 0o755) == _record(b"L", 0o777)
    assert _record(b"F", 0o600) == _record(b"F", 0o644)
    assert _record(b"F", 0o644) != _record(b"F", 0o755)


def test_umask_and_directory_modes_do_not_change_hash_but_executable_bit_does(
    tmp_path: Path,
) -> None:
    skill = _write_skill(tmp_path, "skills/demo")
    script = skill / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    baseline = hash_tree(tmp_path)

    os.chmod(tmp_path / "skills", 0o700)
    os.chmod(skill, 0o711)
    os.chmod(script, 0o600)
    assert hash_tree(tmp_path) == baseline

    os.chmod(script, 0o700)
    assert hash_tree(tmp_path) != baseline


def test_linux_macos_portable_hash_fixture_has_exact_identity(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, "skills/demo")
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Cross-platform fixture\n---\nbody\n",
        encoding="utf-8",
    )
    script = skill / "run.sh"
    script.write_bytes(b"#!/bin/sh\nexit 0\n")
    script.chmod(0o755)
    (skill / "link").symlink_to("SKILL.md")
    (tmp_path / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "noise").write_text("noise", encoding="utf-8")

    assert hash_tree(tmp_path) == "606608c20f9e18871661f42bb269d418a44ce88b1d5d48f09c7073e629e6b9cf"


def test_nested_gitignore_negation_anchoring_and_discovery(tmp_path: Path) -> None:
    _write_skill(tmp_path, "skills/demo")
    _write_skill(tmp_path, "skills/ignored", "ignored")
    (tmp_path / ".gitignore").write_text(
        "/root-only.txt\nskills/ignored/\n*.tmp\n",
        encoding="utf-8",
    )
    (tmp_path / "root-only.txt").write_text("ignored", encoding="utf-8")
    (tmp_path / "skills" / "root-only.txt").write_text("included", encoding="utf-8")
    (tmp_path / "skills" / ".gitignore").write_text(
        "*.log\n!demo/keep.log\n",
        encoding="utf-8",
    )
    demo = tmp_path / "skills" / "demo"
    (demo / "ignored.log").write_text("ignored", encoding="utf-8")
    (demo / "keep.log").write_text("kept", encoding="utf-8")

    artifacts = discover_skills(tmp_path, PurePosixPath("skills"))

    assert [artifact.relative_path.as_posix() for artifact in artifacts] == ["demo"]
    baseline = hash_tree(tmp_path)
    (tmp_path / "root-only.txt").write_text("changed", encoding="utf-8")
    (demo / "ignored.log").write_text("changed", encoding="utf-8")
    assert hash_tree(tmp_path) == baseline
    (demo / "keep.log").write_text("changed", encoding="utf-8")
    assert hash_tree(tmp_path) != baseline


def test_gitignore_is_identity_bearing_and_unignored_files_remain_identity_bearing(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path, "skills/demo")
    ignore = tmp_path / ".gitignore"
    ignore.write_text("*.tmp\n", encoding="utf-8")
    baseline = hash_tree(tmp_path)

    (tmp_path / "noise.tmp").write_text("ignored", encoding="utf-8")
    assert hash_tree(tmp_path) == baseline
    (tmp_path / "ordinary.txt").write_text("included", encoding="utf-8")
    assert hash_tree(tmp_path) != baseline
    ordinary_hash = hash_tree(tmp_path)
    ignore.write_text("*.tmp\n# identity-bearing comment\n", encoding="utf-8")
    assert hash_tree(tmp_path) != ordinary_hash


def test_path_descriptor_and_cache_share_gitignore_inventory(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write_skill(source, "skills/demo")
    (source / ".gitignore").write_text("generated/\n", encoding="utf-8")
    generated = source / "generated"
    generated.mkdir()
    (generated / "large.bin").write_bytes(b"ignored")
    root_fd = os.open(source, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        assert hash_tree_at(root_fd) == hash_tree(source)
    finally:
        os.close(root_fd)

    resolved = resolve_sources(_config(source), tmp_path / "cache")[0]

    assert not (resolved.root / "generated").exists()
    assert (resolved.root / ".gitignore").is_file()
    assert resolved.tree_hash == hash_tree(source) == hash_tree(resolved.root)


def test_trailing_recursive_glob_matches_git_across_evidence_layers(tmp_path: Path) -> None:
    source = tmp_path / "source"
    skill = _write_skill(source, "skills/demo")
    (skill / "keep.txt").write_text("skill keep", encoding="utf-8")
    (skill / "drop.txt").write_text("skill drop", encoding="utf-8")
    (source / "abc" / "def").mkdir(parents=True)
    (source / "abc" / "drop.txt").write_text("abc drop", encoding="utf-8")
    (source / "abc" / "def" / "keep.txt").write_text("abc keep", encoding="utf-8")
    (source / "pruned").mkdir()
    (source / "pruned" / "keep.txt").write_text("parent remains ignored", encoding="utf-8")
    (source / ".gitignore").write_text(
        "abc/**\n"
        "!abc/def/\n"
        "!abc/def/keep.txt\n"
        "skills/**\n"
        "!skills/demo/\n"
        "!skills/demo/SKILL.md\n"
        "!skills/demo/keep.txt\n"
        "pruned/\n"
        "!pruned/keep.txt\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", source], check=True)

    status = subprocess.run(
        [
            "git",
            "-c",
            "core.excludesFile=/dev/null",
            "-C",
            source,
            "status",
            "--short",
            "--ignored",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    git_classification = {line[3:]: line[:2] for line in status}
    assert git_classification["abc/def/keep.txt"] == "??"
    assert git_classification["abc/drop.txt"] == "!!"
    assert git_classification["skills/demo/SKILL.md"] == "??"
    assert git_classification["skills/demo/keep.txt"] == "??"
    assert git_classification["skills/demo/drop.txt"] == "!!"
    assert git_classification["pruned/keep.txt"] == "!!"

    inventory = {path.relative_to(source).as_posix() for path in _inventory_paths(source)}
    assert {"abc", "abc/def", "abc/def/keep.txt", "skills/demo/SKILL.md"} <= inventory
    assert {"abc/drop.txt", "skills/demo/drop.txt", "pruned"}.isdisjoint(inventory)
    path_artifacts = discover_skills(source, PurePosixPath("skills"))
    path_hash = hash_tree(source)
    root_fd = os.open(source, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        assert discover_skills_at(root_fd, PurePosixPath("skills")) == path_artifacts
        assert hash_tree_at(root_fd) == path_hash
    finally:
        os.close(root_fd)

    resolved = resolve_sources(_config(source), tmp_path / "cache")[0]

    assert (resolved.root / "abc/def/keep.txt").read_text(encoding="utf-8") == "abc keep"
    assert not (resolved.root / "abc/drop.txt").exists()
    assert (resolved.root / "skills/demo/keep.txt").is_file()
    assert not (resolved.root / "skills/demo/drop.txt").exists()
    assert not (resolved.root / "pruned").exists()
    validate_snapshot_tree(resolved.root)
    assert resolved.tree_hash == path_hash == hash_tree(resolved.root)
    assert resolve_sources(_config(source), tmp_path / "cache")[0] == resolved

    (source / "abc/drop.txt").write_text("ignored change", encoding="utf-8")
    assert hash_tree(source) == path_hash
    (source / "abc/def/keep.txt").write_text("included change", encoding="utf-8")
    assert hash_tree(source) != path_hash


def test_cache_is_algorithm_namespaced_and_rejects_injected_ignored_entries(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _write_skill(source, "skills/demo")
    (source / ".gitignore").write_text("generated/\n", encoding="utf-8")
    config = _config(source)
    resolved = resolve_sources(config, tmp_path / "cache")[0]

    assert resolved.root.parent.name == "sha256-portable-v2"
    injected = resolved.root / "generated"
    injected.mkdir()
    (injected / "payload").write_text("must not be exposed", encoding="utf-8")

    with pytest.raises(SourceError, match="ignored entry.*filtered snapshot"):
        validate_snapshot_tree(resolved.root)
    with pytest.raises(SourceError, match="cache entry is corrupt"):
        resolve_sources(config, tmp_path / "cache")


def test_new_locks_declare_portable_algorithm_and_legacy_is_not_silently_accepted(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _write_skill(source, "skills/demo")
    config = _config(source)
    lock = build_lock(config, resolve_sources(config, tmp_path / "cache"))

    document = yaml.safe_load(serialize_lock(lock))
    assert document["schema_version"] == 2
    assert document["hash_algorithm"] == "sha256-portable-v2"

    legacy = replace(lock, schema_version=1, hash_algorithm="sha256-legacy-v1")
    with pytest.raises(ResolutionError, match="legacy hash algorithm.*run.*lock"):
        resolve_desired_state(config, legacy)
