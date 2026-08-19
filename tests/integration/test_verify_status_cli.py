from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import yaml

from skill_delegator import receipts
from skill_delegator.cli import main


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_config(project: Path, *, initialize_git: bool = False) -> Path:
    config = project / "config"
    config.mkdir(parents=True)
    source = project / "source" / "skills" / "one"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text(
        "---\nname: one\ndescription: fixture\n---\nbody\n", encoding="utf-8"
    )
    documents = {
        "authority.yaml": {
            "schema_version": 1,
            "authority": {"id": "test", "fail_closed": True, "fixture_policy": "none"},
        },
        "sources.yaml": {
            "schema_version": 1,
            "sources": [
                {
                    "id": "example",
                    "type": "filesystem",
                    "location": "../source",
                    "skill_root": "skills",
                }
            ],
        },
        "pool.yaml": {"schema_version": 1, "skills": ["example/one"]},
        "delegations.yaml": {
            "schema_version": 1,
            "targets": [{"id": "worker", "root": "../target", "grants": ["example/one"]}],
        },
    }
    for filename, document in documents.items():
        (config / filename).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    if initialize_git:
        _git(project, "init", "-q")
        _git(project, "config", "user.email", "test@example.invalid")
        _git(project, "config", "user.name", "Test")
        _git(project, "add", ".")
        _git(project, "commit", "-qm", "fixture")
    assert main(["lock", "--config", str(config)]) == 0
    if initialize_git:
        _git(project, "add", "config/skill-lock.yaml")
        _git(project, "commit", "-qm", "lock")
    return config


def _write_git_config(project: Path) -> tuple[Path, str]:
    source_repo = project / "git-source"
    source_repo.mkdir(parents=True)
    _git(source_repo, "init", "-q")
    _git(source_repo, "config", "user.email", "test@example.invalid")
    _git(source_repo, "config", "user.name", "Test")
    skill = source_repo / "skills" / "one"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: one\ndescription: git fixture\n---\nbody\n", encoding="utf-8"
    )
    _git(source_repo, "add", ".")
    _git(source_repo, "commit", "-qm", "fixture")
    commit = _git(source_repo, "rev-parse", "HEAD")

    config = project / "config"
    config.mkdir()
    documents = {
        "authority.yaml": {
            "schema_version": 1,
            "authority": {"id": "test", "fail_closed": True, "fixture_policy": "none"},
        },
        "sources.yaml": {
            "schema_version": 1,
            "sources": [
                {
                    "id": "upstream",
                    "type": "git",
                    "location": str(source_repo),
                    "skill_root": "skills",
                    "track": commit,
                }
            ],
        },
        "pool.yaml": {"schema_version": 1, "skills": ["upstream/one"]},
        "delegations.yaml": {
            "schema_version": 1,
            "targets": [{"id": "worker", "root": "../target", "grants": ["upstream/one"]}],
        },
    }
    for filename, document in documents.items():
        (config / filename).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert main(["lock", "--config", str(config)]) == 0
    return config, commit


def _snapshot(root: Path) -> tuple[tuple[str, str, str], ...]:
    if not root.exists():
        return ()
    records = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            records.append((relative, "link", os.readlink(path)))
        elif path.is_file():
            records.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        else:
            records.append((relative, "dir", ""))
    return tuple(records)


def test_verify_writes_deterministic_receipt_and_status_is_strictly_read_only(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    target = project / "target"
    target_before = _snapshot(target)
    config_before = _snapshot(config)

    assert main(["status", "--config", str(config)]) == 0
    human = capsys.readouterr()
    assert human.out == "converged: 1/1 links verified across 1 target\n"
    assert human.err == ""
    assert not (project / "var" / "receipts").exists()
    assert _snapshot(target) == target_before
    assert _snapshot(config) == config_before

    assert main(["status", "--json", "--config", str(config)]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["result"] == "converged"
    assert document["operation_summary"]["verified_links"] == 1
    assert not (project / "var" / "receipts").exists()

    assert main(["verify", "--config", str(config)]) == 0
    first = capsys.readouterr()
    assert first.err == ""
    receipt_path = Path(first.out.strip().split("receipt: ", 1)[1])
    first_bytes = receipt_path.read_bytes()
    assert receipt_path.parent == project / "var" / "receipts"
    assert _snapshot(target) == target_before
    assert _snapshot(config) == config_before

    assert main(["verify", "--config", str(config)]) == 0
    second = capsys.readouterr()
    assert Path(second.out.strip().split("receipt: ", 1)[1]) == receipt_path
    assert receipt_path.read_bytes() == first_bytes
    assert len(list(receipt_path.parent.glob("*.json"))) == 1


def test_verify_distinguishes_drift_from_hostile_target_without_traceback(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    link = project / "target" / "example" / "one"
    link.unlink()

    assert main(["verify", "--config", str(config)]) == 1
    drift = capsys.readouterr()
    assert "drift" in drift.out
    assert "managed-link-missing" in drift.out
    assert "Traceback" not in drift.err

    metadata = project / "target" / ".skill-delegator" / "managed.json"
    metadata.write_text("{}", encoding="utf-8")
    assert main(["status", "--config", str(config)]) == 3
    hostile = capsys.readouterr()
    assert hostile.out.startswith("invalid:")
    assert "Traceback" not in hostile.err


def test_offline_git_ungranted_cache_tamper_never_publishes_receipt(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config, commit = _write_git_config(project)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    lock = yaml.safe_load((config / "skill-lock.yaml").read_text(encoding="utf-8"))
    locked_source = lock["sources"][0]
    snapshot = project / "var" / "cache" / "sources" / "upstream" / commit
    tamper = snapshot / "ungranted.txt"
    tamper.write_text("not granted to any target\n", encoding="utf-8")

    assert main(["verify", "--config", str(config)]) == 1
    verify_drift = capsys.readouterr()
    assert verify_drift.err == ""
    assert verify_drift.out.startswith("drift: 0/1 links verified across 1 target\n")
    assert "source-snapshot-hash-mismatch" in verify_drift.out
    assert "receipt:" not in verify_drift.out
    receipts_root = project / "var" / "receipts"
    assert not receipts_root.exists()
    before_status = _snapshot(project / "var")

    assert main(["status", "--config", str(config)]) == 1
    status_drift = capsys.readouterr()
    assert status_drift == verify_drift
    assert _snapshot(project / "var") == before_status
    assert not receipts_root.exists()

    tamper.unlink()
    assert main(["verify", "--config", str(config)]) == 0
    converged = capsys.readouterr()
    receipt = Path(converged.out.strip().split("receipt: ", 1)[1])
    document = json.loads(receipt.read_text(encoding="utf-8"))
    assert len(list(receipts_root.glob("*.json"))) == 1
    assert document["locked_sources"] == [
        {
            "source_id": "upstream",
            "type": "git",
            "revision_kind": "resolved_commit",
            "revision": commit,
            "tree_identity": locked_source["tree_hash"],
        }
    ]


def test_receipt_hashes_exact_config_and_lock_bytes_and_captures_detached_commit(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "repository"
    config = _write_config(project, initialize_git=True)
    expected_commit = _git(project, "rev-parse", "HEAD")
    _git(project, "checkout", "--detach", "-q", expected_commit)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()

    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])
    document = json.loads(receipt.read_text())

    assert document["repository"] == {"available": True, "commit": expected_commit}
    assert {item["name"]: item["sha256"] for item in document["config_hashes"]} == {
        name: hashlib.sha256((config / name).read_bytes()).hexdigest()
        for name in (
            "authority.yaml",
            "delegations.yaml",
            "pool.yaml",
            "skill-lock.yaml",
            "sources.yaml",
        )
    }


def test_non_git_repository_records_explicit_unavailable_commit(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])

    assert json.loads(receipt.read_text())["repository"] == {
        "available": False,
        "commit": None,
    }


def test_untracked_nested_config_does_not_capture_unrelated_ancestor_commit(
    tmp_path: Path, capsys
) -> None:
    outer = tmp_path / "outer"
    outer.mkdir()
    _git(outer, "init", "-q")
    _git(outer, "config", "user.email", "test@example.invalid")
    _git(outer, "config", "user.name", "Test")
    (outer / "owned.txt").write_text("outer repository\n", encoding="utf-8")
    _git(outer, "add", "owned.txt")
    _git(outer, "commit", "-qm", "outer")
    config = _write_config(outer / "untracked-project")
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()

    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])

    assert json.loads(receipt.read_text())["repository"] == {
        "available": False,
        "commit": None,
    }


def test_dirty_tracked_config_bytes_make_repository_commit_unavailable(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "repository"
    config = _write_config(project, initialize_git=True)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    with (config / "authority.yaml").open("a", encoding="utf-8") as stream:
        stream.write("# dirty current bytes\n")
    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])
    assert json.loads(receipt.read_text())["repository"] == {"available": False, "commit": None}


def test_symlinked_tracked_config_input_never_hashes_external_bytes(tmp_path: Path, capsys) -> None:
    project = tmp_path / "repository"
    config = _write_config(project, initialize_git=True)
    external = tmp_path / "external-authority.yaml"
    external.write_bytes((config / "authority.yaml").read_bytes())
    (config / "authority.yaml").unlink()
    (config / "authority.yaml").symlink_to(external)
    capsys.readouterr()

    assert main(["verify", "--config", str(config)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "regular file" in output.err
    assert "Traceback" not in output.err
    assert not (project / "var" / "receipts").exists()


def test_commit_with_tracked_symlink_entry_is_explicitly_unavailable(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "repository"
    config = _write_config(project, initialize_git=True)
    authority_bytes = (config / "authority.yaml").read_bytes()
    external = tmp_path / "external-authority.yaml"
    external.write_bytes(authority_bytes)
    (config / "authority.yaml").unlink()
    (config / "authority.yaml").symlink_to(external)
    _git(project, "add", "config/authority.yaml")
    _git(project, "commit", "-qm", "track authority symlink")
    (config / "authority.yaml").unlink()
    (config / "authority.yaml").write_bytes(authority_bytes)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()

    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])
    assert json.loads(receipt.read_text())["repository"] == {"available": False, "commit": None}


def test_commit_binding_requires_git_blob_bytes_to_equal_current_bytes(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "repository"
    config = _write_config(project, initialize_git=True)
    capsys.readouterr()
    assert main(["apply", "--config", str(config)]) == 0
    capsys.readouterr()
    with (config / "authority.yaml").open("a", encoding="utf-8") as stream:
        stream.write("# differs from commit blob\n")
    assert main(["verify", "--config", str(config)]) == 0
    receipt = Path(capsys.readouterr().out.strip().split("receipt: ", 1)[1])
    document = json.loads(receipt.read_text())
    current_hash = hashlib.sha256((config / "authority.yaml").read_bytes()).hexdigest()
    committed = _git(project, "show", "HEAD:config/authority.yaml").encode()
    assert hashlib.sha256(committed).hexdigest() != current_hash
    assert document["repository"] == {"available": False, "commit": None}


def test_receipt_ancestor_filesystem_failures_are_bounded_by_cli(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    for failure in ("fsync", "open", "close"):
        project = tmp_path / failure / "project"
        config = _write_config(project)
        capsys.readouterr()
        assert main(["apply", "--config", str(config)]) == 0
        capsys.readouterr()
        real_fsync, real_open, real_close = receipts.os.fsync, receipts.os.open, receipts.os.close
        root_metadata = os.stat("/", follow_symlinks=False)
        root_identity = (root_metadata.st_dev, root_metadata.st_ino)
        fired = False

        def fail_fsync(fd, _failure=failure, _real_fsync=real_fsync):
            nonlocal fired
            if _failure == "fsync" and not fired:
                fired = True
                raise OSError("injected ancestor fsync failure")
            return _real_fsync(fd)

        def fail_open(
            path, flags, mode=0o777, *, dir_fd=None, _failure=failure, _real_open=real_open
        ):
            nonlocal fired
            if _failure == "open" and path == "receipts" and not fired:
                fired = True
                raise OSError("injected ancestor open failure")
            return _real_open(path, flags, mode, dir_fd=dir_fd)

        def fail_close(fd, _failure=failure, _real_close=real_close, _root_identity=root_identity):
            nonlocal fired
            try:
                metadata = os.fstat(fd)
                is_root = (metadata.st_dev, metadata.st_ino) == _root_identity
            except OSError:
                is_root = False
            if _failure == "close" and not fired and is_root:
                fired = True
                _real_close(fd)
                raise OSError("injected ancestor close failure")
            return _real_close(fd)

        monkeypatch.setattr(receipts.os, "fsync", fail_fsync)
        monkeypatch.setattr(receipts.os, "open", fail_open)
        monkeypatch.setattr(receipts.os, "close", fail_close)
        try:
            assert main(["verify", "--config", str(config)]) == 3
            output = capsys.readouterr()
            assert fired
            assert output.out == ""
            assert output.err.startswith("Verify blocked:")
            assert "Traceback" not in output.err
            assert not list((project / "var" / "receipts").glob("*.json"))
        finally:
            monkeypatch.setattr(receipts.os, "fsync", real_fsync)
            monkeypatch.setattr(receipts.os, "open", real_open)
            monkeypatch.setattr(receipts.os, "close", real_close)
