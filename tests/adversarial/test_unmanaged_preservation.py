from __future__ import annotations

import fcntl
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import yaml

from tests.fixture_safety import assert_before_mutation, copy_mutation_fixture

REPOSITORY_ROOT = Path(__file__).parents[2]


def _example(tmp_path: Path) -> Path:
    return copy_mutation_fixture(REPOSITORY_ROOT, tmp_path)


def _run(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    assert_before_mutation(project, project.parent, arguments[0])
    return subprocess.run(
        [sys.executable, "-m", "skill_delegator.cli", *arguments],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_apply_and_remove_preserve_unmanaged_tree_bytes_and_links(tmp_path: Path) -> None:
    project = _example(tmp_path)
    second = project / "tests" / "fixtures" / "example-source" / "second"
    second.mkdir()
    (second / "SKILL.md").write_text(
        "---\nname: second\ndescription: second fixture\n---\n",
        encoding="utf-8",
    )
    pool_path = project / "config" / "pool.yaml"
    pool = yaml.safe_load(pool_path.read_text(encoding="utf-8"))
    pool["skills"].append("example/second")
    pool_path.write_text(yaml.safe_dump(pool, sort_keys=False), encoding="utf-8")
    delegations_path = project / "config" / "delegations.yaml"
    delegations = yaml.safe_load(delegations_path.read_text(encoding="utf-8"))
    for target in delegations["targets"]:
        target["grants"].append("example/second")
    delegations_path.write_text(yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8")
    targets = [project / "var" / "example-targets" / name for name in ("reviewer", "worker")]
    outside = tmp_path / "outside"
    outside.write_text("outside\n", encoding="utf-8")
    sentinels: list[tuple[Path, str, Path]] = []
    for index, target in enumerate(targets):
        nested = target / "unmanaged" / "nested.txt"
        nested.parent.mkdir(parents=True)
        nested.write_text(f"sentinel-{index}\n", encoding="utf-8")
        unmanaged_link = target / "unmanaged-link"
        unmanaged_link.symlink_to(outside)
        sentinels.append((nested, _digest(nested), unmanaged_link))

    assert _run(project, "lock").returncode == 0
    assert _run(project, "apply").returncode == 0
    for nested, digest, unmanaged_link in sentinels:
        assert _digest(nested) == digest
        assert unmanaged_link.is_symlink() and Path(os.readlink(unmanaged_link)) == outside

    delegations = yaml.safe_load(delegations_path.read_text(encoding="utf-8"))
    for target in delegations["targets"]:
        target["grants"] = ["example/hello"]
    delegations_path.write_text(yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8")
    assert _run(project, "apply", "--yes").returncode == 0

    for target, (nested, digest, unmanaged_link) in zip(targets, sentinels, strict=True):
        assert (target / "example" / "hello").is_symlink()
        assert not (target / "example" / "second").exists()
        assert _digest(nested) == digest
        assert unmanaged_link.is_symlink() and Path(os.readlink(unmanaged_link)) == outside


def test_concurrent_apply_times_out_without_mutating_managed_or_unmanaged_state(
    tmp_path: Path,
) -> None:
    project = _example(tmp_path)
    assert _run(project, "lock").returncode == 0
    assert _run(project, "apply").returncode == 0
    root = project / "var" / "example-targets" / "worker"
    sentinel = root / "unmanaged.txt"
    sentinel.write_text("preserve\n", encoding="utf-8")
    managed = root / ".skill-delegator" / "managed.json"
    managed_before = managed.read_bytes()
    lock_path = root / ".skill-delegator" / "operation.lock"
    manifest = project / "tests" / "fixtures" / "example-source" / "hello" / "SKILL.md"
    manifest.write_text(
        "---\nname: hello\ndescription: changed fixture\n---\nHello.\n",
        encoding="utf-8",
    )
    assert _run(project, "lock").returncode == 0

    with lock_path.open("r+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = _run(project, "apply", "--lock-timeout", "0.01")

    assert result.returncode == 5
    assert "timeout" in result.stderr
    assert "Traceback" not in result.stderr
    assert managed.read_bytes() == managed_before
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
