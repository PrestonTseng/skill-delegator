from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from tests.fixture_safety import copy_mutation_fixture, run_cli

REPOSITORY_ROOT = Path(__file__).parents[2]


def _run(project: Path, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = run_cli(
        project / "config",
        project.parent,
        [*arguments, "--config", str(project / "config")],
        cwd=project,
    )
    assert result.returncode == expected, (arguments, result.stdout, result.stderr)
    assert "Traceback" not in result.stderr
    return result


def _git(project: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(project), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    if not root.exists():
        return ()
    result: list[tuple[str, str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result.append((relative, "link", os.readlink(path)))
        elif path.is_file():
            result.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        else:
            result.append((relative, "directory", ""))
    return tuple(result)


def _copy_main_example(tmp_path: Path) -> Path:
    project = copy_mutation_fixture(REPOSITORY_ROOT, tmp_path, "main-example")
    (project / ".gitignore").write_bytes((REPOSITORY_ROOT / ".gitignore").read_bytes())
    _git(project, "init", "-q", "-b", "main")
    _git(project, "config", "user.name", "Skill Delegator Test")
    _git(project, "config", "user.email", "test@example.invalid")
    _git(project, "add", ".")
    _git(project, "commit", "-qm", "copied main example")
    return project


def _receipt_path(output: str) -> Path:
    return Path(output.strip().split("receipt: ", 1)[1])


def test_copied_main_example_full_cli_flow_converges_and_is_idempotent(tmp_path: Path) -> None:
    project = _copy_main_example(tmp_path)
    config = project / "config"
    tracked_before = _git(project, "status", "--porcelain=v1", "--untracked-files=all")
    source_before = _snapshot(project / "tests" / "fixtures" / "example-source")
    config_before = _snapshot(config)

    assert _run(project, "validate").stdout == (
        "Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets\n"
    )
    assert _run(project, "lock").stdout == "Locked 1 skill from 1 source\n"
    resolved = json.loads(_run(project, "resolve", "--json").stdout)
    assert [target["id"] for target in resolved["targets"]] == ["reviewer", "worker"]
    first_plan = json.loads(_run(project, "plan", "--json", expected=1).stdout)
    assert [item["action"] for item in first_plan["operations"]] == ["CREATE", "CREATE"]
    assert _run(project, "apply").stdout == "Applied 2 changes to 2 targets\n"
    first_verify = _run(project, "verify")
    assert first_verify.stdout.startswith("converged: 2/2 links verified across 2 targets\n")
    first_receipt = _receipt_path(first_verify.stdout)
    first_receipt_bytes = first_receipt.read_bytes()
    assert first_receipt.name == f"{hashlib.sha256(first_receipt_bytes).hexdigest()}.json"
    status_before = _snapshot(project)
    status = _run(project, "status", "--json")
    assert json.loads(status.stdout)["result"] == "converged"
    assert _snapshot(project) == status_before

    for target_id in ("reviewer", "worker"):
        root = project / "var" / "example-targets" / target_id
        link = root / "example" / "hello"
        assert link.is_symlink()
        assert Path(os.readlink(link)) == (
            project
            / "var"
            / "cache"
            / "sources"
            / "example"
            / "sha256-portable-v2"
            / "c61f839e88b0e993f7b89f17de0536eaa90fa22c6646c00086b40c6abbcdb78f"
            / "hello"
        )
        managed = json.loads((root / ".skill-delegator" / "managed.json").read_text())
        assert managed["manager"] == "skill-delegator"
        assert [entry["artifact_id"] for entry in managed["entries"]] == ["example/hello"]

    assert _snapshot(config) == config_before
    assert _snapshot(project / "tests" / "fixtures" / "example-source") == source_before
    assert _git(project, "status", "--porcelain=v1", "--untracked-files=all") == tracked_before

    assert _run(project, "validate").returncode == 0
    assert _run(project, "lock").stdout == "Locked 1 skill from 1 source\n"
    assert (
        _run(project, "resolve", "--json").stdout
        == json.dumps(resolved, sort_keys=True, separators=(",", ":")) + "\n"
    )
    second_plan = json.loads(_run(project, "plan", "--json").stdout)
    assert not any(
        item["action"] in {"CREATE", "REPLACE", "REMOVE"} for item in second_plan["operations"]
    )
    assert sum(item["action"] == "KEEP" for item in second_plan["operations"]) == 2
    assert _run(project, "apply").stdout == "Already converged\n"
    second_receipt = _receipt_path(_run(project, "verify").stdout)
    assert second_receipt == first_receipt
    assert second_receipt.read_bytes() == first_receipt_bytes
    assert len(list(first_receipt.parent.glob("*.json"))) == 1
    final_before_status = _snapshot(project)
    assert _run(project, "status").stdout == ("converged: 2/2 links verified across 2 targets\n")
    assert _snapshot(project) == final_before_status
    assert _snapshot(config) == config_before
    assert _snapshot(project / "tests" / "fixtures" / "example-source") == source_before
    assert _git(project, "status", "--porcelain=v1", "--untracked-files=all") == tracked_before
