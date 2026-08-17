from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).parents[2]
GUARD_DIAGNOSTIC = "pytest safety guard: refusing generic tests:"
LEAKING_TEST = (
    "tests/adversarial/test_lock_tampering.py::"
    "test_malformed_managed_state_blocks_plan_without_mutation[malformed-json]"
)
SAFE_TEST = (
    "tests/integration/test_validate_cli.py::test_validate_accepts_main_example_and_reports_counts"
)
EXPECTED_CONFIG_ENTRIES = (
    "README.md",
    "authority.yaml",
    "delegations.yaml",
    "pool.yaml",
    "skill-lock.yaml",
    "sources.yaml",
)


def _isolated_repository(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(
        REPOSITORY_ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", ".venv", "dist", "var", "*.pyc", "__pycache__"),
    )
    return destination


def _snapshot(root: Path) -> tuple[tuple[str, str, int, int, str], ...]:
    records: list[tuple[str, str, int, int, str]] = []
    for path in [root, *sorted(root.rglob("*"))]:
        metadata = path.lstat()
        relative = "." if path == root else path.relative_to(root).as_posix()
        if stat.S_ISLNK(metadata.st_mode):
            kind, payload = "symlink", os.readlink(path)
        elif stat.S_ISDIR(metadata.st_mode):
            kind, payload = "directory", ""
        else:
            kind, payload = "file", path.read_bytes().hex()
        records.append((relative, kind, metadata.st_mode, metadata.st_mtime_ns, payload))
    return tuple(records)


def _run_pytest(repository: Path, test: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository / "src")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", test],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _run_guard_probe(repository: Path, sentinel: Path) -> subprocess.CompletedProcess[str]:
    probe = repository / "test_guard_probe.py"
    probe.write_text(
        "from pathlib import Path\n\n"
        "def test_guard_probe_body():\n"
        f"    Path({str(sentinel)!r}).write_text('BODY_RAN', encoding='utf-8')\n",
        encoding="utf-8",
    )
    return _run_pytest(repository, probe.name)


def _assert_guard_refused(result: subprocess.CompletedProcess[str], sentinel: Path) -> None:
    assert result.returncode == 4, (result.stdout, result.stderr)
    assert GUARD_DIAGNOSTIC in result.stderr
    assert "1 passed" not in result.stdout
    assert sentinel.read_text(encoding="utf-8") == "UNCHANGED"


def test_authority_config_aborts_before_previously_leaking_test_can_mutate(tmp_path: Path) -> None:
    repository = _isolated_repository(tmp_path, "authority-copy")
    sentinel = tmp_path / "external-sentinel"
    sentinel.mkdir()
    (sentinel / "keep.txt").write_text("immutable sentinel\n", encoding="utf-8")
    before = _snapshot(sentinel)

    authority_path = repository / "config" / "authority.yaml"
    authority = yaml.safe_load(authority_path.read_text(encoding="utf-8"))
    authority["authority"] = {
        "id": "real-authority",
        "fail_closed": True,
        "fixture_policy": "none",
    }
    authority_path.write_text(yaml.safe_dump(authority, sort_keys=False), encoding="utf-8")
    delegations_path = repository / "config" / "delegations.yaml"
    delegations = yaml.safe_load(delegations_path.read_text(encoding="utf-8"))
    for target in delegations["targets"]:
        target["root"] = str(sentinel)
    delegations_path.write_text(yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8")

    result = _run_pytest(repository, LEAKING_TEST)

    assert result.returncode != 0
    assert GUARD_DIAGNOSTIC in result.stderr
    assert "1 passed" not in result.stdout
    assert _snapshot(sentinel) == before
    assert not (sentinel / ".skill-delegator").exists()
    assert not any(path.is_symlink() for path in sentinel.rglob("*"))
    assert not (repository / "var" / "cache").exists()
    assert not (repository / "var" / "receipts").exists()


def test_safe_generic_repository_still_starts_and_runs_tests(tmp_path: Path) -> None:
    repository = _isolated_repository(tmp_path, "safe-copy")

    result = _run_pytest(repository, SAFE_TEST)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "1 passed" in result.stdout
    assert GUARD_DIAGNOSTIC not in result.stderr


@pytest.mark.parametrize("filename", EXPECTED_CONFIG_ENTRIES)
def test_modified_safe_config_entry_aborts_before_probe_body(tmp_path: Path, filename: str) -> None:
    repository = _isolated_repository(tmp_path, f"modified-{filename}")
    sentinel = tmp_path / f"modified-{filename}.sentinel"
    sentinel.write_text("UNCHANGED", encoding="utf-8")
    path = repository / "config" / filename
    if filename == "delegations.yaml":
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document["targets"][0]["reviewer_extra_field"] = "still-confined"
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b"\n# non-exact safe config\n")

    result = _run_guard_probe(repository, sentinel)

    _assert_guard_refused(result, sentinel)


@pytest.mark.parametrize("change", ["extra", "missing"])
def test_changed_safe_config_entry_set_aborts_before_probe_body(
    tmp_path: Path, change: str
) -> None:
    repository = _isolated_repository(tmp_path, f"entry-set-{change}")
    sentinel = tmp_path / f"entry-set-{change}.sentinel"
    sentinel.write_text("UNCHANGED", encoding="utf-8")
    if change == "extra":
        (repository / "config" / "extra.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    else:
        (repository / "config" / "pool.yaml").unlink()

    result = _run_guard_probe(repository, sentinel)

    _assert_guard_refused(result, sentinel)


@pytest.mark.parametrize("entry_kind", ["symlink", "directory", "fifo"])
def test_non_regular_safe_config_entry_aborts_before_probe_body(
    tmp_path: Path, entry_kind: str
) -> None:
    repository = _isolated_repository(tmp_path, f"non-regular-{entry_kind}")
    sentinel = tmp_path / f"non-regular-{entry_kind}.sentinel"
    sentinel.write_text("UNCHANGED", encoding="utf-8")
    path = repository / "config" / "pool.yaml"
    path.unlink()
    if entry_kind == "symlink":
        path.symlink_to(repository / "config" / "authority.yaml")
    elif entry_kind == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)

    result = _run_guard_probe(repository, sentinel)

    _assert_guard_refused(result, sentinel)


@pytest.mark.parametrize(
    "failure",
    [
        "authority",
        "sources",
        "pool",
        "delegations",
        "skill-lock",
        "unhashable-source-id",
        "unreadable",
    ],
)
def test_malformed_or_unreadable_root_config_aborts_pytest(tmp_path: Path, failure: str) -> None:
    repository = _isolated_repository(tmp_path, f"{failure}-copy")
    authority = repository / "config" / "authority.yaml"
    if failure == "unreadable":
        authority.chmod(0)
    elif failure == "unhashable-source-id":
        sources_path = repository / "config" / "sources.yaml"
        sources = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
        sources["sources"][0]["id"] = ["unhashable"]
        sources_path.write_text(yaml.safe_dump(sources, sort_keys=False), encoding="utf-8")
    else:
        (repository / "config" / f"{failure}.yaml").write_text(
            "? [invalid, mapping]\n: value\n", encoding="utf-8"
        )
    try:
        result = _run_pytest(repository, SAFE_TEST)
    finally:
        authority.chmod(0o644)

    assert result.returncode == 4, (result.stdout, result.stderr)
    assert GUARD_DIAGNOSTIC in result.stderr
    assert "1 passed" not in result.stdout


def test_root_generated_path_symlink_escape_aborts_pytest(tmp_path: Path) -> None:
    repository = _isolated_repository(tmp_path, "symlink-copy")
    outside = tmp_path / "outside-generated-state"
    outside.mkdir()
    (repository / "var").symlink_to(outside, target_is_directory=True)

    result = _run_pytest(repository, SAFE_TEST)

    assert result.returncode != 0
    assert GUARD_DIAGNOSTIC in result.stderr
    assert "symlink ancestor" in result.stderr
    assert tuple(outside.iterdir()) == ()
