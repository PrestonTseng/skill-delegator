from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

import pytest

from skill_delegator.errors import SourceError
from skill_delegator.models import AuthorityConfig, SourceSpec
from skill_delegator.safe_paths import AnchoredDirectory, open_anchored_directory
from skill_delegator.source_store import resolve_sources


def _write_skill(root: Path) -> None:
    skill = root / "skills" / "hello"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: hello\ndescription: Native macOS fixture\n---\nbody\n",
        encoding="utf-8",
    )


def _config(source: SourceSpec) -> AuthorityConfig:
    return AuthorityConfig(
        authority_id="test",
        fail_closed=True,
        fixture_policy="none",
        sources=(source,),
        pool=(),
        targets=(),
    )


def test_filesystem_lock_never_requires_descriptor_pseudo_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source"
    _write_skill(source_root)
    source = SourceSpec("local", "filesystem", source_root, PurePosixPath("skills"), None)

    def forbidden_descriptor_path(_self: AnchoredDirectory) -> Path:
        raise AssertionError("security-sensitive traversal must use dir_fd operations")

    monkeypatch.setattr(
        AnchoredDirectory,
        "descriptor_path",
        property(forbidden_descriptor_path),
    )

    resolved = resolve_sources(_config(source), tmp_path / "cache")

    assert resolved[0].root == (
        tmp_path / "cache" / "local" / "sha256-portable-v2" / resolved[0].revision
    )
    assert resolved[0].skills[0].canonical_id == "local/hello"


def test_existing_cache_child_is_opened_relative_to_retained_parent(tmp_path: Path) -> None:
    parent = tmp_path / "cache"
    child = parent / "revision"
    child.mkdir(parents=True)

    with open_anchored_directory(parent, description="test-cache") as anchored:
        descriptor = anchored.open_existing_child("revision", description="cache-entry")
        try:
            opened = os.fstat(descriptor)
            lexical = child.stat(follow_symlinks=False)
            assert (opened.st_dev, opened.st_ino) == (lexical.st_dev, lexical.st_ino)
        finally:
            os.close(descriptor)


def test_existing_cache_child_replacement_is_detected_after_validation(tmp_path: Path) -> None:
    parent = tmp_path / "cache"
    child = parent / "revision"
    child.mkdir(parents=True)

    with open_anchored_directory(parent, description="test-cache") as anchored:
        descriptor = anchored.open_existing_child("revision", description="cache-entry")
        try:
            child.rename(parent / "retained-revision")
            child.mkdir()
            with pytest.raises(SourceError, match="cache-entry-identity-changed"):
                anchored.verify_existing_child("revision", descriptor, description="cache-entry")
        finally:
            os.close(descriptor)


def test_existing_cache_child_rejects_symlink(tmp_path: Path) -> None:
    parent = tmp_path / "cache"
    outside = tmp_path / "outside"
    parent.mkdir()
    outside.mkdir()
    (parent / "revision").symlink_to(outside, target_is_directory=True)

    with (
        open_anchored_directory(parent, description="test-cache") as anchored,
        pytest.raises(SourceError, match="unsafe-symlink-or-nondirectory"),
    ):
        anchored.open_existing_child("revision", description="cache-entry")
