from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_CONFIG = REPOSITORY_ROOT / "config"


def run_cli(config_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skill_delegator.cli", "validate", "--config", str(config_dir)],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_validate_accepts_main_example_and_reports_counts() -> None:
    result = run_cli(EXAMPLE_CONFIG)

    assert result.returncode == 0
    assert result.stdout == "Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets\n"
    assert result.stderr == ""


def test_validate_rejects_invalid_config_with_precise_stderr(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)
    path = config_dir / "delegations.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["targets"][0]["grants"] = "not-a-list"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    result = run_cli(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "delegations.yaml" in result.stderr
    assert "grants" in result.stderr


def test_validate_rejects_invalid_utf8_without_traceback(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)
    (config_dir / "authority.yaml").write_bytes(b"\xff")

    result = run_cli(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "authority.yaml" in result.stderr
    assert "invalid UTF-8" in result.stderr
    assert "Traceback" not in result.stderr


def test_validate_rejects_unhashable_yaml_mapping_key_without_traceback(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)
    (config_dir / "authority.yaml").write_text("? [a, b]\n: c\n", encoding="utf-8")

    result = run_cli(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "authority.yaml" in result.stderr
    assert "unhashable mapping key" in result.stderr
    assert "Traceback" not in result.stderr


def test_validate_rejects_nul_target_for_non_fixture_authority_without_traceback(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)

    authority_path = config_dir / "authority.yaml"
    authority = yaml.safe_load(authority_path.read_text(encoding="utf-8"))
    authority["authority"].update({"id": "non-fixture", "fixture_policy": "none"})
    authority_path.write_text(yaml.safe_dump(authority, sort_keys=False), encoding="utf-8")

    delegations_path = config_dir / "delegations.yaml"
    delegations = yaml.safe_load(delegations_path.read_text(encoding="utf-8"))
    delegations["targets"][0]["root"] = "before\0after"
    delegations_path.write_text(yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8")

    result = run_cli(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "delegations.yaml at targets.0.root:" in result.stderr
    assert "NUL" in result.stderr
    assert "Traceback" not in result.stderr


def test_validate_rejects_lone_surrogate_path_without_traceback(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(EXAMPLE_CONFIG, config_dir)

    authority_path = config_dir / "authority.yaml"
    authority = yaml.safe_load(authority_path.read_text(encoding="utf-8"))
    authority["authority"].update({"id": "non-fixture", "fixture_policy": "none"})
    authority_path.write_text(yaml.safe_dump(authority, sort_keys=False), encoding="utf-8")

    sources_path = config_dir / "sources.yaml"
    sources = yaml.safe_load(sources_path.read_text(encoding="utf-8"))
    sources["sources"][0]["skill_root"] = "before\udfffafter"
    sources_path.write_text(yaml.safe_dump(sources, sort_keys=False), encoding="utf-8")

    result = run_cli(config_dir)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "sources.yaml at sources.0.skill_root:" in result.stderr
    assert "surrogate" in result.stderr
    assert "Traceback" not in result.stderr
