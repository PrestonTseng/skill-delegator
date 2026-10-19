from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
import yaml

from skill_delegator import exact_plan
from tests.fixture_safety import copy_mutation_fixture, run_cli


def _write_config(
    project: Path,
    *,
    target_ids: tuple[str, ...] = ("worker",),
    skill_names: tuple[str, ...] = ("one",),
) -> Path:
    config = project / "config"
    config.mkdir(parents=True)
    for skill_name in skill_names:
        skill = project / "source" / skill_name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: fixture {skill_name}\n---\nbody\n",
            encoding="utf-8",
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
                    "skill_root": ".",
                }
            ],
        },
        "pool.yaml": {
            "schema_version": 1,
            "skills": [f"example/{skill_name}" for skill_name in skill_names],
        },
        "delegations.yaml": {
            "schema_version": 1,
            "targets": [
                {
                    "id": target_id,
                    "root": f"../targets/{target_id}",
                    "grants": [f"example/{skill_name}" for skill_name in skill_names],
                }
                for target_id in target_ids
            ],
        },
    }
    for name, document in documents.items():
        (config / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    assert run_cli(config, project.parent, ["lock", "--config", str(config)]) == 0
    return config


def _write_plan(config: Path, boundary: Path, path: Path, capsys, *, target: str | None = None):
    arguments = ["plan", "--out", str(path), "--config", str(config)]
    if target is not None:
        arguments[1:1] = ["--target", target]
    result = run_cli(config, boundary, arguments)
    captured = capsys.readouterr()
    report = json.loads(captured.out) if captured.out else {}
    return result, captured, report


def _bound_apply(
    config: Path,
    boundary: Path,
    path: Path,
    digest: str,
    *,
    target: str | None = None,
    yes: bool = False,
) -> int:
    arguments = [
        "apply",
        "--plan-file",
        str(path),
        "--plan-sha256",
        digest,
        "--config",
        str(config),
    ]
    if target is not None:
        arguments[1:1] = ["--target", target]
    if yes:
        arguments[1:1] = ["--yes"]
    return run_cli(config, boundary, arguments)


def _rewrite_artifact(path: Path, transform) -> str:
    document = json.loads(path.read_bytes())
    transform(document)
    payload = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def test_plan_out_is_deterministic_canonical_and_reports_digest(tmp_path: Path, capsys) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    first_result, first_output, first_report = _write_plan(config, tmp_path, first, capsys)
    second_result, second_output, second_report = _write_plan(config, tmp_path, second, capsys)

    assert first_result == second_result == 1
    assert first_output.err == second_output.err == ""
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes().endswith(b"\n")
    assert (
        first.read_bytes()
        == (
            json.dumps(json.loads(first.read_bytes()), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
    )
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    assert first_report == {"plan_file": str(first), "plan_sha256": digest}
    assert second_report == {"plan_file": str(second), "plan_sha256": digest}
    artifact = json.loads(first.read_bytes())
    assert artifact["schema_version"] == 1
    assert set(artifact) == {
        "authority_id",
        "blocked",
        "change_state",
        "config_inputs",
        "lock_sha256",
        "operations",
        "schema_version",
        "target_fingerprints",
        "target_scope",
    }
    assert artifact["authority_id"] == "test"
    assert artifact["target_scope"] is None
    assert artifact["change_state"] == "changes"
    assert {item["name"] for item in artifact["config_inputs"]} == {
        "authority.yaml",
        "delegations.yaml",
        "pool.yaml",
        "skill-lock.yaml",
        "sources.yaml",
    }
    assert artifact["lock_sha256"] == next(
        item["sha256"] for item in artifact["config_inputs"] if item["name"] == "skill-lock.yaml"
    )
    assert artifact["target_fingerprints"][0]["target_id"] == "worker"
    assert artifact["operations"][0]["action"] == "CREATE"


def test_bound_apply_consumes_exact_plan_and_reports_digest(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    plan_path = tmp_path / "approved.json"
    plan_result, plan_output, report = _write_plan(config, tmp_path, plan_path, capsys)
    assert plan_result == 1
    assert plan_output.err == ""

    result = run_cli(
        config,
        tmp_path,
        [
            "apply",
            "--plan-file",
            str(plan_path),
            "--plan-sha256",
            report["plan_sha256"],
            "--config",
            str(config),
        ],
    )
    captured = capsys.readouterr()

    assert result == 0
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "changed": 1,
        "plan_sha256": report["plan_sha256"],
        "result": "applied",
        "targets": 1,
    }
    assert (project / "targets" / "worker" / "example" / "one").is_symlink()


def test_bound_apply_rejects_tampered_bytes_and_digest_without_residue(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    plan_path = tmp_path / "approved.json"
    _, _, report = _write_plan(config, tmp_path, plan_path, capsys)
    plan_path.write_bytes(plan_path.read_bytes() + b" ")

    assert _bound_apply(config, tmp_path, plan_path, report["plan_sha256"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SHA-256 does not match" in captured.err
    assert not (project / "targets").exists()

    tampered_digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert _bound_apply(config, tmp_path, plan_path, tampered_digest) == 3
    captured = capsys.readouterr()
    assert "not canonical" in captured.err
    assert not (project / "targets").exists()


@pytest.mark.parametrize("case", ["malformed", "duplicate", "unknown"])
def test_bound_apply_rejects_malformed_duplicate_and_unknown_fields(
    case: str, tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    plan_path = tmp_path / "approved.json"
    _write_plan(config, tmp_path, plan_path, capsys)
    if case == "malformed":
        payload = b"{\n"
    elif case == "duplicate":
        original = plan_path.read_text(encoding="utf-8").rstrip()
        payload = (
            original.replace(
                '{"authority_id":"test",',
                '{"authority_id":"test","authority_id":"test",',
                1,
            ).encode()
            + b"\n"
        )
    else:
        document = json.loads(plan_path.read_bytes())
        document["unknown"] = True
        payload = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()
    plan_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()

    assert _bound_apply(config, tmp_path, plan_path, digest) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("Apply blocked:")
    assert not (project / "targets").exists()


def test_bound_apply_rejects_wrong_authority_and_target_scope(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project, target_ids=("alpha", "beta"))
    capsys.readouterr()
    plan_path = tmp_path / "approved.json"
    _, _, report = _write_plan(config, tmp_path, plan_path, capsys, target="alpha")

    assert _bound_apply(config, tmp_path, plan_path, report["plan_sha256"], target="beta") == 3
    captured = capsys.readouterr()
    assert "target selector differs" in captured.err

    digest = _rewrite_artifact(
        plan_path, lambda document: document.__setitem__("authority_id", "other")
    )
    assert _bound_apply(config, tmp_path, plan_path, digest, target="alpha") == 3
    captured = capsys.readouterr()
    assert "stale or does not match" in captured.err
    assert not (project / "targets").exists()


@pytest.mark.parametrize("stale", ["config", "lock", "source", "target", "operations"])
def test_bound_apply_rejects_each_stale_identity_without_target_or_receipt_residue(
    stale: str, tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    plan_path = tmp_path / "approved.json"
    _, _, report = _write_plan(config, tmp_path, plan_path, capsys)
    digest = report["plan_sha256"]
    if stale == "config":
        with (config / "authority.yaml").open("a", encoding="utf-8") as stream:
            stream.write("\n")
    elif stale == "lock":
        with (config / "skill-lock.yaml").open("a", encoding="utf-8") as stream:
            stream.write("# reviewed bytes changed\n")
    elif stale == "source":
        cached = next((project / "var" / "cache" / "sources").rglob("SKILL.md"))
        cached.write_text(cached.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
    elif stale == "target":
        target = project / "targets" / "worker"
        target.mkdir(parents=True)
        (target / "unmanaged.txt").write_text("new", encoding="utf-8")
    else:
        digest = _rewrite_artifact(
            plan_path,
            lambda document: document["operations"].clear(),
        )

    assert _bound_apply(config, tmp_path, plan_path, digest) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert not (project / "targets" / "worker" / "example" / "one").exists()
    assert not (project / "var" / "receipts").exists()


def test_plan_out_refuses_existing_and_symlink_paths(tmp_path: Path, capsys) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()
    existing = tmp_path / "existing.json"
    existing.write_text("sentinel", encoding="utf-8")

    result, captured, _ = _write_plan(config, tmp_path, existing, capsys)
    assert result == 3
    assert captured.out == ""
    assert existing.read_text(encoding="utf-8") == "sentinel"

    target = tmp_path / "target.json"
    target.write_text("sentinel", encoding="utf-8")
    linked = tmp_path / "linked.json"
    linked.symlink_to(target)
    result, captured, _ = _write_plan(config, tmp_path, linked, capsys)
    assert result == 3
    assert captured.out == ""
    assert linked.is_symlink()
    assert target.read_text(encoding="utf-8") == "sentinel"


def test_blocked_plan_artifact_records_blocker_state_without_mutations(
    tmp_path: Path, capsys
) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    occupied = project / "targets" / "worker" / "example" / "one"
    occupied.parent.mkdir(parents=True)
    occupied.write_text("unmanaged", encoding="utf-8")
    plan_path = tmp_path / "blocked.json"

    result, captured, report = _write_plan(config, tmp_path, plan_path, capsys)

    assert result == 3
    assert captured.err == ""
    assert report["plan_sha256"] == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    artifact = json.loads(plan_path.read_bytes())
    assert artifact["change_state"] == "blocked"
    assert artifact["blocked"]
    assert not [
        operation
        for operation in artifact["operations"]
        if operation["action"] in {"CREATE", "REPLACE", "REMOVE"}
    ]


def test_scoped_multi_file_artifact_carries_every_delegation_input(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project, target_ids=("alpha", "beta"))
    legacy = yaml.safe_load((config / "delegations.yaml").read_text(encoding="utf-8"))
    (config / "delegations.yaml").unlink()
    delegation_directory = config / "delegations"
    delegation_directory.mkdir()
    for target in legacy["targets"]:
        (delegation_directory / f"{target['id']}.yaml").write_text(
            yaml.safe_dump({"schema_version": 1, "target": target}, sort_keys=False),
            encoding="utf-8",
        )
    capsys.readouterr()
    plan_path = tmp_path / "alpha.json"

    result, captured, report = _write_plan(config, tmp_path, plan_path, capsys, target="alpha")

    assert result == 1
    assert captured.err == ""
    artifact = json.loads(plan_path.read_bytes())
    assert artifact["target_scope"] == "alpha"
    assert {item["name"] for item in artifact["config_inputs"]} == {
        "authority.yaml",
        "delegations/alpha.yaml",
        "delegations/beta.yaml",
        "pool.yaml",
        "skill-lock.yaml",
        "sources.yaml",
    }
    assert _bound_apply(config, tmp_path, plan_path, report["plan_sha256"], target="alpha") == 0


def test_plan_publication_failure_leaves_no_public_or_temporary_residue(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()
    plan_path = tmp_path / "approved.json"

    def fail_link(*_args, **_kwargs):
        raise OSError("injected")

    monkeypatch.setattr(exact_plan.os, "link", fail_link)
    result, captured, _ = _write_plan(config, tmp_path, plan_path, capsys)

    assert result == 3
    assert captured.out == ""
    assert not plan_path.exists()
    assert not list(tmp_path.glob(".approved.json.*.tmp"))


def test_plan_publication_rolls_back_when_directory_sync_fails_after_link(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _write_config(tmp_path / "project")
    capsys.readouterr()
    plan_path = tmp_path / "approved.json"
    real_fsync = exact_plan.os.fsync
    directory_syncs = 0

    def fail_first_directory_sync(descriptor: int) -> None:
        nonlocal directory_syncs
        if os.path.isdir(f"/proc/self/fd/{descriptor}"):
            directory_syncs += 1
            if directory_syncs == 1:
                raise OSError("injected")
        real_fsync(descriptor)

    monkeypatch.setattr(exact_plan.os, "fsync", fail_first_directory_sync)
    result, captured, _ = _write_plan(config, tmp_path, plan_path, capsys)

    assert result == 3
    assert captured.out == ""
    assert not plan_path.exists()
    assert not list(tmp_path.glob(".approved.json.*.tmp"))


def test_plan_paths_reject_symlinked_parent_components(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    real_directory = tmp_path / "real-directory"
    real_directory.mkdir()
    linked_directory = tmp_path / "linked-directory"
    linked_directory.symlink_to(real_directory, target_is_directory=True)
    unsafe_output = linked_directory / "approved.json"

    result, captured, _ = _write_plan(config, tmp_path, unsafe_output, capsys)
    assert result == 3
    assert captured.out == ""
    assert not (real_directory / "approved.json").exists()

    safe_plan = real_directory / "safe.json"
    _, _, report = _write_plan(config, tmp_path, safe_plan, capsys)
    unsafe_input = linked_directory / "safe.json"
    assert _bound_apply(config, tmp_path, unsafe_input, report["plan_sha256"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert not (project / "targets").exists()


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_bound_apply_refuses_unsafe_input_path_types(kind: str, tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project)
    capsys.readouterr()
    real_plan = tmp_path / "real.json"
    _, _, report = _write_plan(config, tmp_path, real_plan, capsys)
    unsafe = tmp_path / "unsafe"
    if kind == "symlink":
        unsafe.symlink_to(real_plan)
    elif kind == "directory":
        unsafe.mkdir()
    else:
        os.mkfifo(unsafe)

    assert _bound_apply(config, tmp_path, unsafe, report["plan_sha256"]) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert not (project / "targets").exists()


def test_bound_remove_still_requires_yes(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project, skill_names=("one", "two"))
    capsys.readouterr()
    create_plan = tmp_path / "create.json"
    _, _, create_report = _write_plan(config, tmp_path, create_plan, capsys)
    assert _bound_apply(config, tmp_path, create_plan, create_report["plan_sha256"]) == 0
    capsys.readouterr()
    delegations = yaml.safe_load((config / "delegations.yaml").read_text(encoding="utf-8"))
    delegations["targets"][0]["grants"] = ["example/one"]
    (config / "delegations.yaml").write_text(
        yaml.safe_dump(delegations, sort_keys=False), encoding="utf-8"
    )
    remove_plan = tmp_path / "remove.json"
    remove_result, remove_output, remove_report = _write_plan(config, tmp_path, remove_plan, capsys)
    assert remove_result == 1, remove_output.err

    assert _bound_apply(config, tmp_path, remove_plan, remove_report["plan_sha256"]) == 4
    refused = capsys.readouterr()
    managed = project / "targets" / "worker" / "example" / "two"
    assert "pass --yes" in refused.err
    assert managed.is_symlink()

    assert _bound_apply(config, tmp_path, remove_plan, remove_report["plan_sha256"], yes=True) == 0
    assert not managed.exists()


def test_target_scoped_bound_apply_does_not_touch_other_target(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    config = _write_config(project, target_ids=("alpha", "beta"))
    capsys.readouterr()
    hostile = project / "targets" / "beta" / "example" / "one"
    hostile.parent.mkdir(parents=True)
    hostile.write_text("unmanaged", encoding="utf-8")
    plan_path = tmp_path / "alpha.json"
    _, _, report = _write_plan(config, tmp_path, plan_path, capsys, target="alpha")

    assert _bound_apply(config, tmp_path, plan_path, report["plan_sha256"], target="alpha") == 0
    assert (project / "targets" / "alpha" / "example" / "one").is_symlink()
    assert hostile.read_text(encoding="utf-8") == "unmanaged"


def test_safe_example_supports_bound_e2e_and_legacy_commands_remain_unchanged(
    tmp_path: Path, capsys
) -> None:
    repository = Path(__file__).parents[2]
    project = copy_mutation_fixture(repository, tmp_path)
    config = project / "config"
    assert run_cli(config, tmp_path, ["lock", "--config", str(config)]) == 0
    capsys.readouterr()
    legacy_plan = run_cli(config, tmp_path, ["plan", "--json", "--config", str(config)])
    legacy_output = capsys.readouterr()
    assert legacy_plan == 1
    assert set(json.loads(legacy_output.out)) == {"blocked", "operations"}

    plan_path = tmp_path / "safe-example.json"
    _, _, report = _write_plan(config, tmp_path, plan_path, capsys)
    assert _bound_apply(config, tmp_path, plan_path, report["plan_sha256"]) == 0
    capsys.readouterr()
    assert run_cli(config, tmp_path, ["apply", "--config", str(config)]) == 0
    legacy_apply = capsys.readouterr()
    assert legacy_apply.out == "Already converged\n"
