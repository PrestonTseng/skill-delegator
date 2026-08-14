from __future__ import annotations

import builtins
import importlib
import sys
import tomllib
from pathlib import Path

import pytest


def test_cli_import_and_help_survive_missing_fcntl(monkeypatch, capsys) -> None:
    real_import = builtins.__import__

    def without_fcntl(name, *args, **kwargs):
        if name == "fcntl":
            raise ImportError("unsupported platform")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_fcntl)
    sys.modules.pop("skill_delegator.reconciler", None)
    sys.modules.pop("skill_delegator.cli", None)
    cli = importlib.import_module("skill_delegator.cli")
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    assert "skillctl" in capsys.readouterr().out


def test_unsupported_platform_has_one_bounded_operational_diagnostic(monkeypatch, capsys) -> None:
    from skill_delegator import cli

    monkeypatch.setattr(cli.os, "name", "nt")
    assert cli.main(["validate"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "skillctl error: V1 requires POSIX\n"


def test_project_metadata_declares_linux_posix_without_windows_support() -> None:
    project = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())
    classifiers = project["project"]["classifiers"]

    assert "Operating System :: POSIX" in classifiers
    assert "Operating System :: POSIX :: Linux" in classifiers
    assert not any("Windows" in classifier for classifier in classifiers)
