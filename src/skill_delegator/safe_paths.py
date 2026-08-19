"""Descriptor-anchored directory traversal for security-sensitive writes."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Self

from skill_delegator.errors import SourceError

_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class AnchoredDirectory:
    """A lexical directory chain retained by descriptor and inode identity."""

    def __init__(
        self, path: Path, fds: list[int], names: list[str], identities: list[tuple[int, int]]
    ):
        self.path = path
        self._fds = fds
        self._names = names
        self._identities = identities

    @property
    def fd(self) -> int:
        return self._fds[-1]

    @property
    def descriptor_path(self) -> Path:
        # Child processes (Git) can traverse the retained descriptor through the
        # parent's proc entry even though the descriptor itself is close-on-exec.
        proc_path = Path(f"/proc/{os.getpid()}/fd/{self.fd}")
        return proc_path if proc_path.exists() else Path(f"/dev/fd/{self.fd}")

    def open_child(self, name: str, *, description: str) -> None:
        if Path(name).parts != (name,) or name in {"", ".", ".."}:
            raise SourceError(f"{description}-invalid-name")
        parent_fd = self.fd
        try:
            try:
                os.mkdir(name, mode=0o755, dir_fd=parent_fd)
            except FileExistsError:
                pass
            child_fd = os.open(name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=parent_fd)
            metadata = os.fstat(child_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                raise NotADirectoryError(name)
        except OSError as error:
            raise SourceError(f"{description}-unsafe-symlink-or-nondirectory") from error
        self._fds.append(child_fd)
        self._names.append(name)
        self._identities.append((metadata.st_dev, metadata.st_ino))
        self.path /= name

    def open_existing_child(self, name: str, *, description: str) -> int:
        """Open one existing direct child directory without following a link."""

        if Path(name).parts != (name,) or name in {"", ".", ".."}:
            raise SourceError(f"{description}-invalid-name")
        self.verify(description=description)
        descriptor = -1
        try:
            descriptor = os.open(name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=self.fd)
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                raise NotADirectoryError(name)
            self.verify(description=description)
            return descriptor
        except OSError as error:
            if descriptor >= 0:
                os.close(descriptor)
            raise SourceError(f"{description}-unsafe-symlink-or-nondirectory") from error
        except Exception:
            if descriptor >= 0:
                os.close(descriptor)
            raise

    def verify(self, *, description: str) -> None:
        """Verify every retained pathname edge still names its opened directory."""

        try:
            root = os.fstat(self._fds[0])
            if (root.st_dev, root.st_ino) != self._identities[0] or not stat.S_ISDIR(root.st_mode):
                raise OSError("anchor identity changed")
            for parent_fd, name, expected in zip(
                self._fds[:-1], self._names, self._identities[1:], strict=True
            ):
                metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or (metadata.st_dev, metadata.st_ino) != expected
                ):
                    raise OSError("directory identity changed")
        except OSError as error:
            raise SourceError(f"{description}-identity-changed") from error

    def close(self) -> None:
        for fd in reversed(self._fds):
            try:
                os.close(fd)
            except OSError:
                pass
        self._fds.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def open_anchored_directory(path: Path, *, description: str) -> AnchoredDirectory:
    """Create/traverse ``path`` from its filesystem anchor without following links."""

    lexical = Path(os.path.abspath(path))
    parts = lexical.parts
    anchor = Path(lexical.anchor)
    fds: list[int] = []
    names: list[str] = []
    identities: list[tuple[int, int]] = []
    try:
        current_fd = os.open(anchor, _DIRECTORY_FLAGS | _NOFOLLOW)
        fds.append(current_fd)
        root = os.fstat(current_fd)
        identities.append((root.st_dev, root.st_ino))
        for name in parts[1:]:
            try:
                os.mkdir(name, mode=0o755, dir_fd=current_fd)
            except FileExistsError:
                pass
            child_fd = os.open(name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=current_fd)
            metadata = os.fstat(child_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                raise NotADirectoryError(name)
            fds.append(child_fd)
            names.append(name)
            identities.append((metadata.st_dev, metadata.st_ino))
            current_fd = child_fd
    except OSError as error:
        for fd in reversed(fds):
            try:
                os.close(fd)
            except OSError:
                pass
        raise SourceError(f"{description}-unsafe-symlink-or-nondirectory") from error
    result = AnchoredDirectory(lexical, fds, names, identities)
    result.verify(description=description)
    return result


def open_existing_anchored_directory(path: Path, *, description: str) -> AnchoredDirectory:
    """Traverse an existing directory chain without following links or creating entries."""

    lexical = Path(os.path.abspath(path))
    fds: list[int] = []
    names: list[str] = []
    identities: list[tuple[int, int]] = []
    try:
        current_fd = os.open(lexical.anchor, _DIRECTORY_FLAGS | _NOFOLLOW)
        fds.append(current_fd)
        root = os.fstat(current_fd)
        identities.append((root.st_dev, root.st_ino))
        for name in lexical.parts[1:]:
            child_fd = os.open(name, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=current_fd)
            metadata = os.fstat(child_fd)
            if not stat.S_ISDIR(metadata.st_mode):
                raise NotADirectoryError(name)
            fds.append(child_fd)
            names.append(name)
            identities.append((metadata.st_dev, metadata.st_ino))
            current_fd = child_fd
    except FileNotFoundError as error:
        for fd in reversed(fds):
            os.close(fd)
        raise SourceError(f"{description}-missing") from error
    except OSError as error:
        for fd in reversed(fds):
            try:
                os.close(fd)
            except OSError:
                pass
        raise SourceError(f"{description}-unsafe-symlink-or-nondirectory") from error
    result = AnchoredDirectory(lexical, fds, names, identities)
    result.verify(description=description)
    return result
