"""Safe deterministic skill discovery and content hashing."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from skill_delegator.errors import SourceError
from skill_delegator.identifiers import canonical_relative_path
from skill_delegator.models import SkillArtifact
from skill_delegator.source_ignore import IgnoreRules

_RUNTIME_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class _UniqueLoader(yaml.SafeLoader):
    """Safe frontmatter loader that rejects duplicate keys."""


def _unique_mapping(
    loader: _UniqueLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                "while constructing frontmatter",
                node.start_mark,
                "unhashable key",
                key_node.start_mark,
            ) from error
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing frontmatter",
                node.start_mark,
                f"duplicate key: {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _validated_root(source_root: Path) -> Path:
    try:
        root = source_root.resolve(strict=True)
    except OSError as error:
        raise SourceError(f"source root cannot be resolved: {source_root}: {error}") from error
    if not root.is_dir():
        raise SourceError(f"source root is not a directory: {source_root}")
    return root


def _validate_relative_root(skill_root: PurePosixPath) -> None:
    if skill_root.is_absolute() or any(part == ".." for part in skill_root.parts):
        raise SourceError(f"skill root must be a confined relative path: {skill_root}")


def _inventory_paths(root: Path, *, reject_ignored: bool = False) -> tuple[Path, ...]:
    paths: list[Path] = []

    def walk(directory: Path, prefix: tuple[bytes, ...], inherited: IgnoreRules) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: os.fsencode(entry.name))
        except OSError as error:
            raise SourceError(f"cannot list source directory {directory}: {error}") from error
        rules = inherited
        ignore = next(
            (entry for entry in entries if os.fsencode(entry.name) == b".gitignore"), None
        )
        if ignore is not None:
            try:
                metadata = ignore.stat(follow_symlinks=False)
                if stat.S_ISREG(metadata.st_mode):
                    rules = rules.extend(prefix, Path(ignore.path).read_bytes())
            except OSError as error:
                raise SourceError(
                    f"cannot read source .gitignore {ignore.path}: {error}"
                ) from error
        for entry in entries:
            name = os.fsencode(entry.name)
            if name == b".git":
                continue
            path = Path(entry.path)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise SourceError(f"cannot inspect source path {path}: {error}") from error
            parts = (*prefix, name)
            directory_entry = stat.S_ISDIR(metadata.st_mode)
            if rules.ignored(parts, directory=directory_entry):
                if reject_ignored:
                    raise SourceError(f"ignored entry present in filtered snapshot: {path}")
                continue
            paths.append(path)
            if directory_entry:
                walk(path, parts, rules)

    walk(root, (), IgnoreRules())
    return tuple(paths)


def _assert_confined_symlinks(tree_root: Path, source_root: Path) -> None:
    for path in _inventory_paths(tree_root):
        if not path.is_symlink():
            continue
        try:
            resolved = path.resolve(strict=True)
        except OSError as error:
            raise SourceError(f"broken symlink in source: {path}: {error}") from error
        if not resolved.is_relative_to(source_root):
            raise SourceError(f"symlink escape from source root: {path} -> {resolved}")


def validate_source_tree(source_root: Path) -> Path:
    """Validate every symlink in a source tree, excluding ``.git`` only."""

    source = _validated_root(source_root)
    _assert_confined_symlinks(source, source)
    return source


def validate_snapshot_tree(source_root: Path) -> Path:
    """Validate links remain confined after a tree is copied to a new root."""

    source = validate_source_tree(source_root)
    for path in _inventory_paths(source, reject_ignored=True):
        if path.is_symlink() and Path(os.readlink(path)).is_absolute():
            raise SourceError(f"symlink escape from copied snapshot root: {path}")
    return source


def _parse_frontmatter(text: str, display_path: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise SourceError(
            f"{display_path}: invalid SKILL.md frontmatter: missing opening delimiter"
        )
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise SourceError(
            f"{display_path}: invalid SKILL.md frontmatter: missing closing delimiter"
        ) from error
    try:
        document = yaml.load("\n".join(lines[1:end]), Loader=_UniqueLoader)
    except yaml.YAMLError as error:
        raise SourceError(f"{display_path}: invalid SKILL.md frontmatter: {error}") from error
    if not isinstance(document, dict):
        raise SourceError(f"{display_path}: invalid SKILL.md frontmatter: expected mapping")
    name = document.get("name")
    description = document.get("description")
    if not isinstance(name, str) or not name.strip():
        raise SourceError(f"{display_path}: invalid SKILL.md frontmatter: name is required")
    if _RUNTIME_NAME_PATTERN.fullmatch(name) is None:
        raise SourceError(
            f"{display_path}: invalid SKILL.md frontmatter: name is not a safe runtime id"
        )
    if not isinstance(description, str) or not description.strip():
        raise SourceError(f"{display_path}: invalid SKILL.md frontmatter: description is required")
    return name, description


def _frontmatter_bytes(payload: bytes, display_path: str) -> tuple[str, str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeError as error:
        raise SourceError(f"{display_path}: invalid SKILL.md frontmatter: {error}") from error
    return _parse_frontmatter(text, display_path)


def _frontmatter(path: Path) -> tuple[str, str]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise SourceError(f"{path}: invalid SKILL.md frontmatter: {error}") from error
    return _frontmatter_bytes(payload, str(path))


def inspect_skill(skill_directory: Path) -> SkillArtifact:
    """Freshly validate one exact skill directory and return metadata/content identity."""

    root = validate_source_tree(skill_directory)
    name, description = _frontmatter(root / "SKILL.md")
    return SkillArtifact(PurePosixPath("."), name, description, hash_tree(root))


def _filesystem_bytes(value: str | os.PathLike[str], label: str) -> bytes:
    try:
        return os.fsencode(value)
    except UnicodeEncodeError as error:
        display = ascii(os.fspath(value))
        raise SourceError(
            f"{label} cannot be represented as filesystem bytes: {display}"
        ) from error


def _hash_record(digest: Any, kind: bytes, path: bytes, mode: int, payload: bytes) -> None:
    digest.update(kind)
    digest.update(len(path).to_bytes(8, "big"))
    digest.update(path)
    if kind == b"F":
        canonical_mode = 0o755 if mode & 0o111 else 0o644
    elif kind == b"D":
        canonical_mode = 0o755
    elif kind == b"L":
        canonical_mode = 0o777
    else:
        raise SourceError(f"unsupported source entry kind: {kind!r}")
    digest.update(canonical_mode.to_bytes(4, "big"))
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def _hash_tree_with_policy(root: Path, policy_root: Path) -> str:
    """Hash filtered entries using portable modes without following symlinks."""

    root = _validated_root(root)
    policy_root = _validated_root(policy_root)
    if not root.is_relative_to(policy_root):
        raise SourceError(f"hash root is outside source policy root: {root}")
    digest = hashlib.sha256()
    paths: list[tuple[bytes, Path]] = []
    for path in _inventory_paths(policy_root):
        if path == root or not path.is_relative_to(root):
            continue
        relative = PurePosixPath(path.relative_to(root).as_posix())
        encoded_relative = _filesystem_bytes(relative.as_posix(), "source path")
        paths.append((encoded_relative, path))
    for encoded_relative, path in sorted(paths, key=lambda item: item[0]):
        metadata = path.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            target = _filesystem_bytes(os.readlink(path), "symlink target")
            _hash_record(digest, b"L", encoded_relative, mode, target)
        elif stat.S_ISDIR(metadata.st_mode):
            _hash_record(digest, b"D", encoded_relative, mode, b"")
        elif stat.S_ISREG(metadata.st_mode):
            try:
                payload = path.read_bytes()
            except OSError as error:
                raise SourceError(f"cannot hash source file {path}: {error}") from error
            _hash_record(digest, b"F", encoded_relative, mode, payload)
        else:
            raise SourceError(f"unsupported special file in source: {path}")
    return digest.hexdigest()


def hash_tree(root: Path) -> str:
    """Hash a source tree with portable modes and source-local ``.gitignore`` rules."""

    return _hash_tree_with_policy(root, root)


def discover_skills(source_root: Path, skill_root: PurePosixPath) -> tuple[SkillArtifact, ...]:
    """Discover strict ``SKILL.md`` artifacts below a confined skill root."""

    source = _validated_root(source_root)
    _validate_relative_root(skill_root)
    lexical_skill_root = source.joinpath(*skill_root.parts)
    try:
        resolved_skill_root = lexical_skill_root.resolve(strict=True)
    except OSError as error:
        raise SourceError(f"skill root cannot be resolved: {skill_root}: {error}") from error
    if not resolved_skill_root.is_relative_to(source):
        raise SourceError(f"skill root symlink escape: {skill_root}")
    if not resolved_skill_root.is_dir():
        raise SourceError(f"skill root is not a directory: {skill_root}")
    _assert_confined_symlinks(resolved_skill_root, source)

    artifacts: list[SkillArtifact] = []
    seen: set[PurePosixPath] = set()
    for manifest in sorted(
        (path for path in _inventory_paths(source) if path.name == "SKILL.md"),
        key=lambda path: os.fsencode(path.relative_to(source)),
    ):
        if not manifest.is_relative_to(resolved_skill_root) or not manifest.is_file():
            continue
        directory = manifest.parent
        relative = PurePosixPath(directory.relative_to(resolved_skill_root).as_posix())
        if relative == PurePosixPath("."):
            raise SourceError(f"{manifest}: skill must be in a directory below skill_root")
        if relative in seen:
            raise SourceError(f"duplicate artifact path: {relative}")
        try:
            relative.as_posix().encode("utf-8")
        except UnicodeEncodeError as error:
            raise SourceError(
                f"skill path cannot form a UTF-8 canonical id: {relative.as_posix()!a}"
            ) from error
        if not canonical_relative_path(relative):
            raise SourceError(f"skill path cannot form a canonical id: {relative.as_posix()!r}")
        seen.add(relative)
        name, description = _frontmatter(manifest)
        artifacts.append(
            SkillArtifact(
                relative_path=relative,
                runtime_name=name,
                description=description,
                sha256=_hash_tree_with_policy(directory, source),
            )
        )
    return tuple(sorted(artifacts, key=lambda artifact: artifact.relative_path.as_posix()))
