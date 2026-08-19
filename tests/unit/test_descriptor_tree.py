from __future__ import annotations

import errno
import os
import stat
from pathlib import Path, PurePosixPath

import pytest

from skill_delegator.descriptor_tree import (
    copy_tree_at,
    copy_tree_into_at,
    discover_skills_at,
    hash_tree_at,
    validate_tree_at,
)
from skill_delegator.errors import SourceError
from skill_delegator.inventory import discover_skills, hash_tree


def _open_directory(path: Path) -> int:
    return os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))


def _write_parity_tree(root: Path) -> None:
    nested = root / "skills" / "group" / "demo"
    nested.mkdir(parents=True)
    manifest = nested / "SKILL.md"
    manifest.write_text(
        "---\nname: demo\ndescription: Descriptor parity\n---\n\nBody.\n",
        encoding="utf-8",
    )
    executable = nested / "run.sh"
    executable.write_bytes(b"#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    (nested / "manifest-link").symlink_to("SKILL.md")
    (root / ".git").mkdir()
    (root / ".git" / "ignored").write_bytes(b"noise")


def test_hash_tree_at_matches_path_hash_for_nested_tree(tmp_path: Path) -> None:
    _write_parity_tree(tmp_path)
    root_fd = _open_directory(tmp_path)
    try:
        validate_tree_at(root_fd, snapshot=False)
        assert hash_tree_at(root_fd) == hash_tree(tmp_path)
    finally:
        os.close(root_fd)


def test_validate_tree_at_rejects_escaping_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (tmp_path / "outside").write_bytes(b"secret")
    (source / "escape").symlink_to("../outside")
    root_fd = _open_directory(source)
    try:
        with pytest.raises(SourceError, match="symlink escape"):
            validate_tree_at(root_fd, snapshot=False)
    finally:
        os.close(root_fd)


def test_validate_tree_at_allows_internal_absolute_link_only_for_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    payload = source / "payload"
    payload.write_bytes(b"content")
    (source / "link").symlink_to(payload)
    root_fd = _open_directory(source)
    try:
        validate_tree_at(root_fd, snapshot=False)
        with pytest.raises(SourceError, match="copied snapshot"):
            validate_tree_at(root_fd, snapshot=True)
    finally:
        os.close(root_fd)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX FIFOs")
def test_descriptor_operations_reject_unsupported_file_kind(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "pipe")
    root_fd = _open_directory(tmp_path)
    try:
        with pytest.raises(SourceError, match="unsupported special file"):
            validate_tree_at(root_fd, snapshot=False)
        with pytest.raises(SourceError, match="unsupported special file"):
            hash_tree_at(root_fd)
    finally:
        os.close(root_fd)


def test_discover_skills_at_matches_inventory_metadata_and_hashes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_parity_tree(source)
    second = source / "skills" / "z-last"
    second.mkdir()
    (second / "SKILL.md").write_text(
        "---\nname: zed\ndescription: Last skill\n---\n",
        encoding="utf-8",
    )
    root_fd = _open_directory(source)
    try:
        assert discover_skills_at(root_fd, PurePosixPath("skills")) == discover_skills(
            source, PurePosixPath("skills")
        )
    finally:
        os.close(root_fd)


def test_copy_tree_at_preserves_hash_modes_and_links_but_excludes_git(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_parity_tree(source)
    destination = tmp_path / "copy"
    root_fd = _open_directory(source)
    try:
        copy_tree_at(root_fd, destination)
    finally:
        os.close(root_fd)

    assert hash_tree(destination) == hash_tree(source)
    assert stat.S_IMODE((destination / "skills/group/demo/run.sh").stat().st_mode) == 0o755
    assert os.readlink(destination / "skills/group/demo/manifest-link") == "SKILL.md"
    assert not (destination / ".git").exists()


def test_copy_tree_into_at_populates_precreated_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_parity_tree(source)
    destination = tmp_path / "copy"
    destination.mkdir(mode=0o700)
    source_fd = _open_directory(source)
    destination_fd = _open_directory(destination)
    try:
        copy_tree_into_at(source_fd, destination_fd)
        validate_tree_at(destination_fd, snapshot=True)
        assert hash_tree_at(destination_fd) == hash_tree(source)
    finally:
        os.close(destination_fd)
        os.close(source_fd)

    assert hash_tree(destination) == hash_tree(source)
    assert os.readlink(destination / "skills/group/demo/manifest-link") == "SKILL.md"
    assert not (destination / ".git").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte-oriented filenames")
def test_descriptor_hash_and_copy_preserve_non_utf8_filename_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_bytes = os.fsencode(source)
    try:
        with open(os.path.join(source_bytes, b"payload-\xff"), "wb") as stream:
            stream.write(b"payload")
        os.symlink(b"payload-\xff", os.path.join(source_bytes, b"link-\xfe"))
    except OSError as error:
        if error.errno == errno.EILSEQ:
            pytest.skip("filesystem rejects non-UTF8 filename bytes")
        raise
    destination = tmp_path / "copy"
    root_fd = _open_directory(source)
    try:
        assert hash_tree_at(root_fd) == hash_tree(source)
        copy_tree_at(root_fd, destination)
    finally:
        os.close(root_fd)

    assert hash_tree(destination) == hash_tree(source)
    assert os.path.lexists(os.path.join(os.fsencode(destination), b"link-\xfe"))
