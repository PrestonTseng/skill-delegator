from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

import pytest

from skill_delegator.errors import SourceError
from skill_delegator.inventory import discover_skills, hash_tree


def write_skill(root: Path, relative: str, name: str = "runtime") -> Path:
    directory = root / relative
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A test skill\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return directory


def test_discovers_nested_skills_in_canonical_relative_order(tmp_path: Path) -> None:
    write_skill(tmp_path, "skills/z-last", "z")
    write_skill(tmp_path, "skills/group/a-first", "a")

    artifacts = discover_skills(tmp_path, PurePosixPath("skills"))

    assert [item.relative_path.as_posix() for item in artifacts] == ["group/a-first", "z-last"]
    assert [item.runtime_name for item in artifacts] == ["a", "z"]
    assert all(len(item.sha256) == 64 for item in artifacts)


@pytest.mark.parametrize(
    "content",
    [
        "No frontmatter\n",
        "---\nname: only-name\n---\n",
        "---\ndescription: only-description\n---\n",
        "---\nname: ''\ndescription: nope\n---\n",
        "---\nname: duplicate\nname: duplicate-again\ndescription: nope\n---\n",
    ],
)
def test_rejects_malformed_or_missing_frontmatter(tmp_path: Path, content: str) -> None:
    skill = tmp_path / "skill" / "bad"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(content, encoding="utf-8")

    with pytest.raises(SourceError, match="SKILL.md.*frontmatter"):
        discover_skills(tmp_path, PurePosixPath("."))


def test_rejects_skill_root_symlink_escape(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside"
    write_skill(outside, "escaped")
    (source / "skills").symlink_to(outside, target_is_directory=True)

    with pytest.raises(SourceError, match="escape|symlink"):
        discover_skills(source, PurePosixPath("skills"))


def test_rejects_symlink_inside_skill_that_escapes_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    skill = write_skill(source, "skill")
    outside = tmp_path / "secret"
    outside.write_text("secret", encoding="utf-8")
    (skill / "leak").symlink_to(outside)

    with pytest.raises(SourceError, match="escape"):
        discover_skills(source, PurePosixPath("."))


def test_tree_hash_covers_paths_modes_symlinks_and_bytes_but_excludes_git(tmp_path: Path) -> None:
    (tmp_path / "file").write_bytes(b"one")
    (tmp_path / "link").symlink_to("file")
    first = hash_tree(tmp_path)

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "noise").write_bytes(b"ignored")
    assert hash_tree(tmp_path) == first

    (tmp_path / "file").write_bytes(b"two")
    assert hash_tree(tmp_path) != first
    second = hash_tree(tmp_path)

    os.chmod(tmp_path / "file", 0o755)
    assert hash_tree(tmp_path) != second
