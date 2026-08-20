"""Immutable, descriptor-bound snapshots of authority configuration inputs."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

_MAX_CONFIG_BYTES = 16 * 1024 * 1024
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
if hasattr(os, "O_NOFOLLOW"):
    _DIRECTORY_FLAGS |= os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
if hasattr(os, "O_NOFOLLOW"):
    _FILE_FLAGS |= os.O_NOFOLLOW

DirectoryIdentity = tuple[int, int]
FileIdentity = tuple[int, int, int, int]


@dataclass(frozen=True)
class ConfigInput:
    """Exact bytes and lexical descriptor identities for one input."""

    name: str
    data: bytes
    parent_identity: DirectoryIdentity
    file_identity: FileIdentity


@dataclass(frozen=True)
class ConfigInputSnapshot:
    """The complete immutable input set from which an authority was parsed."""

    config_dir: Path
    config_dir_identity: DirectoryIdentity
    inputs: tuple[ConfigInput, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.inputs)

    def bytes_for(self, name: str) -> bytes:
        for item in self.inputs:
            if item.name == name:
                return item.data
        raise KeyError(name)

    def bytes_by_name(self) -> dict[str, bytes]:
        return {item.name: item.data for item in self.inputs}

    def verifier_identities(self) -> dict[str, tuple[DirectoryIdentity, tuple[int, int, int]]]:
        return {
            item.name: (item.parent_identity, item.file_identity[:2] + (item.file_identity[3],))
            for item in self.inputs
        }


def input_from_open_file(
    name: str, data: bytes, parent_stat: os.stat_result, file_stat: os.stat_result
) -> ConfigInput:
    """Construct an immutable record from already-verified open descriptors."""

    return ConfigInput(
        name,
        data,
        (parent_stat.st_dev, parent_stat.st_ino),
        (file_stat.st_dev, file_stat.st_ino, stat.S_IFMT(file_stat.st_mode), file_stat.st_size),
    )


def _read_from_parent(parent_fd: int, name: str, relative_name: str) -> ConfigInput:
    file_fd = -1
    try:
        parent_before = os.fstat(parent_fd)
        lexical = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(lexical.st_mode):
            raise ValueError("configuration snapshot changed")
        file_fd = os.open(name, _FILE_FLAGS, dir_fd=parent_fd)
        opened = os.fstat(file_fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            lexical.st_dev,
            lexical.st_ino,
        ):
            raise ValueError("configuration snapshot changed")
        chunks: list[bytes] = []
        remaining = _MAX_CONFIG_BYTES + 1
        while remaining:
            chunk = os.read(file_fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(file_fd)
        parent_after = os.fstat(parent_fd)
        if (
            len(data) > _MAX_CONFIG_BYTES
            or len(data) != opened.st_size
            or (after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode), after.st_size)
            != (opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode), opened.st_size)
            or (parent_after.st_dev, parent_after.st_ino)
            != (parent_before.st_dev, parent_before.st_ino)
        ):
            raise ValueError("configuration snapshot changed")
        return input_from_open_file(relative_name, data, parent_before, opened)
    except ValueError:
        raise
    except OSError as error:
        raise ValueError("configuration snapshot changed") from error
    finally:
        if file_fd >= 0:
            try:
                os.close(file_fd)
            except OSError as error:
                raise ValueError("configuration snapshot changed") from error


def _delegation_names(config_fd: int) -> tuple[str, tuple[str, ...]]:
    try:
        legacy = os.stat("delegations.yaml", dir_fd=config_fd, follow_symlinks=False)
    except FileNotFoundError:
        legacy = None
    try:
        directory = os.stat("delegations", dir_fd=config_fd, follow_symlinks=False)
    except FileNotFoundError:
        directory = None
    if (legacy is None) == (directory is None):
        raise ValueError("configuration snapshot changed")
    if legacy is not None:
        if not stat.S_ISREG(legacy.st_mode):
            raise ValueError("configuration snapshot changed")
        return "single", ("delegations.yaml",)
    assert directory is not None
    if not stat.S_ISDIR(directory.st_mode):
        raise ValueError("configuration snapshot changed")
    directory_fd = -1
    try:
        directory_fd = os.open("delegations", _DIRECTORY_FLAGS, dir_fd=config_fd)
        opened = os.fstat(directory_fd)
        if (opened.st_dev, opened.st_ino) != (directory.st_dev, directory.st_ino):
            raise ValueError("configuration snapshot changed")
        names = sorted(os.listdir(directory_fd), key=os.fsencode)
        if not names:
            raise ValueError("configuration snapshot changed")
        relative_names = []
        for name in names:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or not name.endswith(".yaml"):
                raise ValueError("configuration snapshot changed")
            relative_names.append(f"delegations/{name}")
        return "multiple", tuple(relative_names)
    except ValueError:
        raise
    except OSError as error:
        raise ValueError("configuration snapshot changed") from error
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)


def capture_current_snapshot(expected: ConfigInputSnapshot) -> ConfigInputSnapshot:
    """Re-capture the expected input domain without following lexical symlinks."""

    config_fd = -1
    delegation_fd = -1
    try:
        config_fd = os.open(expected.config_dir, _DIRECTORY_FLAGS)
        config_stat = os.fstat(config_fd)
        _, delegation_names = _delegation_names(config_fd)
        expected_common = tuple(
            name for name in expected.names if not name.startswith("delegations")
        )
        names = tuple(sorted((*expected_common, *delegation_names), key=os.fsencode))
        if names != expected.names:
            raise ValueError("configuration snapshot changed")
        if any(name.startswith("delegations/") for name in names):
            delegation_fd = os.open("delegations", _DIRECTORY_FLAGS, dir_fd=config_fd)
        inputs = []
        for name in names:
            if name.startswith("delegations/"):
                assert delegation_fd >= 0
                inputs.append(
                    _read_from_parent(delegation_fd, name.removeprefix("delegations/"), name)
                )
            else:
                inputs.append(_read_from_parent(config_fd, name, name))
        return ConfigInputSnapshot(
            expected.config_dir,
            (config_stat.st_dev, config_stat.st_ino),
            tuple(inputs),
        )
    except ValueError:
        raise
    except OSError as error:
        raise ValueError("configuration snapshot changed") from error
    finally:
        if delegation_fd >= 0:
            os.close(delegation_fd)
        if config_fd >= 0:
            os.close(config_fd)


def assert_snapshot_current(snapshot: ConfigInputSnapshot) -> None:
    """Fail closed unless names, identities, types, sizes, and bytes still match."""

    if capture_current_snapshot(snapshot) != snapshot:
        raise ValueError("configuration snapshot changed")
