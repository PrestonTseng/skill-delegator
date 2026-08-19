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
    assert captured.err == "skillctl error: supported platforms are Linux and macOS\n"


def test_unlisted_posix_platform_fails_before_configuration_access(monkeypatch, capsys) -> None:
    from skill_delegator import cli

    monkeypatch.setattr(cli.sys, "platform", "freebsd14")

    def unexpected_load(*_args, **_kwargs):
        raise AssertionError("configuration must not be read on an unsupported platform")

    monkeypatch.setattr(cli, "load_config", unexpected_load)

    assert cli.main(["validate"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "skillctl error: supported platforms are Linux and macOS\n"


def test_macos_reaches_operational_configuration_loading(monkeypatch) -> None:
    from skill_delegator import cli

    monkeypatch.setattr(cli.sys, "platform", "darwin")

    def expected_load(*_args, **_kwargs):
        raise RuntimeError("macOS reached configuration loading")

    monkeypatch.setattr(cli, "load_config", expected_load)

    with pytest.raises(RuntimeError, match="macOS reached configuration loading"):
        cli.main(["validate"])


def test_project_metadata_declares_linux_and_macos_without_windows_support() -> None:
    project = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())
    classifiers = project["project"]["classifiers"]

    assert "Operating System :: POSIX" in classifiers
    assert "Operating System :: POSIX :: Linux" in classifiers
    assert "Operating System :: MacOS" in classifiers
    assert "Operating System :: MacOS :: MacOS X" in classifiers
    assert not any("Windows" in classifier for classifier in classifiers)
