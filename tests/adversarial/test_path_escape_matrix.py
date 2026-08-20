from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixture_safety import copy_mutation_fixture, run_cli

REPOSITORY_ROOT = Path(__file__).parents[2]


def _example(tmp_path: Path) -> Path:
    return copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)


def _run(project: Path, command: str, expected: int) -> subprocess.CompletedProcess[str]:
    result = run_cli(
        project / "config",
        project.parent,
        [command, "--config", str(project / "config")],
        cwd=project,
    )
    assert result.returncode == expected, (result.stdout, result.stderr)
    assert "Traceback" not in result.stderr
    return result


@pytest.mark.parametrize("kind", ["symlink", "file"])
def test_filesystem_source_ancestor_escape_fails_closed_without_cache_publication(
    tmp_path: Path, kind: str
) -> None:
    project = _example(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    shutil.move(str(project / "tests" / "fixtures"), outside / "fixtures")
    shutil.rmtree(project / "tests")
    if kind == "symlink":
        (project / "tests").symlink_to(outside, target_is_directory=True)
    else:
        (project / "tests").write_text("not a directory", encoding="utf-8")

    result = _run(project, "lock", 2)

    assert result.stdout == ""
    assert result.stderr.startswith("Lock error:")
    assert not (project / "var" / "cache").exists()


@pytest.mark.parametrize("kind", ["symlink", "file"])
def test_cache_ancestor_escape_fails_closed_without_outside_writes(
    tmp_path: Path, kind: str
) -> None:
    project = _example(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    if kind == "symlink":
        (project / "var").symlink_to(outside, target_is_directory=True)
    else:
        (project / "var").write_text("not a directory", encoding="utf-8")

    result = _run(project, "lock", 2)

    assert result.stdout == ""
    assert result.stderr.startswith("Lock error:")
    assert tuple(outside.iterdir()) == ()


@pytest.mark.parametrize("kind", ["symlink", "file"])
def test_target_ancestor_escape_fails_validation_without_outside_writes(
    tmp_path: Path, kind: str
) -> None:
    project = _example(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "var").mkdir()
    if kind == "symlink":
        (project / "var" / "example-targets").symlink_to(outside, target_is_directory=True)
    else:
        (project / "var" / "example-targets").write_text("not a directory", encoding="utf-8")

    result = _run(project, "validate", 2)

    assert result.stdout == ""
    assert result.stderr.startswith("Configuration error:")
    assert tuple(outside.iterdir()) == ()


@pytest.mark.parametrize("kind", ["symlink", "file"])
def test_receipt_root_escape_fails_closed_without_outside_publication(
    tmp_path: Path, kind: str
) -> None:
    project = _example(tmp_path)
    _run(project, "lock", 0)
    _run(project, "apply", 0)
    receipts = project / "var" / "receipts"
    outside = tmp_path / "outside"
    outside.mkdir()
    if kind == "symlink":
        receipts.symlink_to(outside, target_is_directory=True)
    else:
        receipts.write_text("not a directory", encoding="utf-8")

    result = _run(project, "verify", 3)

    assert result.stdout == ""
    assert result.stderr.startswith("Verify blocked:")
    assert tuple(outside.iterdir()) == ()
