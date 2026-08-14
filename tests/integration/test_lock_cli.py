from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "config"


def run_lock(config_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skill_delegator.cli", "lock", "--config", str(config_dir)],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_lock_cli_is_byte_stable_and_never_touches_target_roots(tmp_path: Path) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)
    source = project / "source"
    source.mkdir(parents=True)
    skill = source / "hello"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: hello\ndescription: Hello fixture\n---\nbody\n", encoding="utf-8"
    )

    sources = yaml.safe_load((config_dir / "sources.yaml").read_text(encoding="utf-8"))
    sources["sources"][0]["location"] = "../source"
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(sources, sort_keys=False), encoding="utf-8"
    )
    targets = yaml.safe_load((config_dir / "delegations.yaml").read_text(encoding="utf-8"))
    target_roots: list[Path] = []
    for index, target in enumerate(targets["targets"]):
        target["root"] = f"../var/example-targets/target-{index}"
        root = project / "var" / "example-targets" / f"target-{index}"
        root.mkdir(parents=True)
        (root / "sentinel").write_text("untouched", encoding="utf-8")
        target_roots.append(root)
    (config_dir / "delegations.yaml").write_text(
        yaml.safe_dump(targets, sort_keys=False), encoding="utf-8"
    )

    before_targets = {
        root: tuple(sorted(path.relative_to(root) for path in root.rglob("*")))
        for root in target_roots
    }
    first = run_lock(config_dir)
    first_bytes = (config_dir / "skill-lock.yaml").read_bytes()
    second = run_lock(config_dir)

    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout == "Locked 1 skill from 1 source\n"
    assert first.stderr == second.stderr == ""
    assert (config_dir / "skill-lock.yaml").read_bytes() == first_bytes
    after_targets = {
        root: tuple(sorted(path.relative_to(root) for path in root.rglob("*")))
        for root in target_roots
    }
    assert after_targets == before_targets
    assert all(
        (root / "sentinel").read_text(encoding="utf-8") == "untouched" for root in target_roots
    )
