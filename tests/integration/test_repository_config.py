import json
import re
import shlex
import stat
import tomllib
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from skill_delegator.config import load_config

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_checked_out_repository_config_validates() -> None:
    load_config(REPOSITORY_ROOT / "config")


def test_ruff_excludes_provenance_bound_skill_source_snapshots() -> None:
    project = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["tool"]["ruff"]["extend-exclude"] == ["src/skill_source"]


def test_equal_container_root_singular_examples_are_schema_valid_and_use_the_shared_pool() -> None:
    documentation = (REPOSITORY_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    section = documentation.split("## Scoped and Unscoped Root Semantics", 1)[1].split(
        "Deploy the complete configuration", 1
    )[0]
    yaml_block = re.search(r"```yaml\n(?P<body>.*?)```", section, re.DOTALL)
    assert yaml_block is not None
    examples = re.findall(
        r"^# delegations/(?P<filename>[^\n]+)\n(?P<body>.*?)(?=^# delegations/|\Z)",
        yaml_block.group("body"),
        re.MULTILINE | re.DOTALL,
    )
    assert [filename for filename, _ in examples] == ["reviewer.yaml", "worker.yaml"]

    singular_schema = json.loads(
        (REPOSITORY_ROOT / "schemas" / "target-delegation.schema.json").read_text()
    )
    legacy_schema = json.loads(
        (REPOSITORY_ROOT / "schemas" / "delegations.schema.json").read_text()
    )
    registry = Registry().with_resource(
        "delegations.schema.json", Resource.from_contents(legacy_schema)
    )
    validator = Draft202012Validator(singular_schema, registry=registry)
    shared_pool = {"shared/code-review", "shared/testing"}

    for filename, body in examples:
        document = yaml.safe_load(body)
        validator.validate(document)
        assert filename == f"{document['target']['id']}.yaml"
        assert set(document["target"]["grants"]) <= shared_pool


def _assert_ci_contract(workflows_dir: Path) -> None:
    entries = sorted(workflows_dir.iterdir(), key=lambda path: path.name)
    assert [entry.name for entry in entries] == ["ci.yml"]
    workflow_path = workflows_dir / "ci.yml"
    assert stat.S_ISREG(workflow_path.stat(follow_symlinks=False).st_mode)
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    expected_commands = [
        shlex.split("uv sync --locked --python 3.12"),
        shlex.split("uv run --frozen --python 3.12 pytest -q"),
        shlex.split("uv run --frozen --python 3.12 ruff format --check ."),
        shlex.split("uv run --frozen --python 3.12 ruff check ."),
        shlex.split("uv run --frozen --python 3.12 python -m compileall -q src tests"),
        shlex.split(
            "uv run --frozen --python 3.12 pytest -q tests/integration/test_schema_artifacts.py"
        ),
        shlex.split("uv build --python 3.12"),
    ]
    prohibited_subcommands = {"apply", "lock", "status", "verify"}
    ref_condition_markers = ("github.ref", ".ref", "ref_name", "refs/", "branch")

    def assert_no_working_directory(value: object) -> None:
        if isinstance(value, dict):
            assert "working-directory" not in value
            for child in value.values():
                assert_no_working_directory(child)
        elif isinstance(value, list):
            for child in value:
                assert_no_working_directory(child)

    assert_no_working_directory(workflow)
    jobs = workflow["jobs"]
    assert list(jobs) == ["test"]
    job = jobs["test"]
    assert job["runs-on"] == "${{ matrix.os }}"
    assert job["strategy"].get("fail-fast") is False
    matrix = job["strategy"]["matrix"]
    assert matrix == {"os": ["ubuntu-latest", "macos-latest"]}

    conditions = [job.get("if"), *(step.get("if") for step in job["steps"])]
    for condition in (condition for condition in conditions if condition is not None):
        lowered = str(condition).lower()
        assert not any(marker in lowered for marker in ref_condition_markers)

    checkouts = [
        step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")
    ]
    assert len(checkouts) == 1
    checkout_options = checkouts[0].get("with", {})
    assert isinstance(checkout_options, dict)
    assert "ref" not in checkout_options

    run_commands = [shlex.split(step["run"]) for step in job["steps"] if "run" in step]
    for command in run_commands:
        for index, token in enumerate(command[:-1]):
            assert not (
                Path(token).name == "skillctl" and command[index + 1] in prohibited_subcommands
            )
    assert run_commands == expected_commands


def test_ci_runs_the_same_branch_agnostic_repository_gates_on_linux_and_macos() -> None:
    _assert_ci_contract(REPOSITORY_ROOT / ".github" / "workflows")


def _mutated_workflows(tmp_path: Path, mutation: str) -> Path:
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    source = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
    text = source.read_text(encoding="utf-8")
    (workflows_dir / "ci.yml").write_text(text, encoding="utf-8")
    if mutation == "second-workflow":
        (workflows_dir / "release.yml").write_text(text, encoding="utf-8")
        return workflows_dir

    workflow = yaml.safe_load(text)
    jobs = workflow["jobs"]
    first_job = next(iter(jobs.values()))
    if mutation == "second-job":
        jobs["duplicate"] = deepcopy(first_job)
    elif mutation == "missing-macos":
        first_job["strategy"]["matrix"]["os"] = ["ubuntu-latest"]
    elif mutation == "literal-runner":
        first_job["runs-on"] = "ubuntu-latest"
    elif mutation == "fail-fast-default":
        first_job["strategy"].pop("fail-fast", None)
    elif mutation == "fail-fast-true":
        first_job["strategy"]["fail-fast"] = True
    elif mutation == "checkout-ref":
        checkout = next(
            step for step in first_job["steps"] if "actions/checkout@" in step.get("uses", "")
        )
        checkout["with"] = {"ref": "main"}
    elif mutation == "branch-condition":
        first_job["if"] = "github.ref == 'refs/heads/main'"
    elif mutation == "working-directory":
        first_job["steps"][-1]["working-directory"] = "src"
    elif mutation == "job-default-working-directory":
        first_job["defaults"] = {"run": {"working-directory": "src"}}
    elif mutation == "workflow-default-working-directory":
        workflow["defaults"] = {"run": {"working-directory": "src"}}
    elif mutation == "prohibited-command":
        first_job["steps"][-1]["run"] = "uv run skillctl apply --config config"
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    (workflows_dir / "ci.yml").write_text(
        yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8"
    )
    return workflows_dir


@pytest.mark.parametrize(
    "mutation",
    [
        "second-workflow",
        "second-job",
        "missing-macos",
        "literal-runner",
        "fail-fast-default",
        "fail-fast-true",
        "checkout-ref",
        "branch-condition",
        "working-directory",
        "job-default-working-directory",
        "workflow-default-working-directory",
        "prohibited-command",
    ],
)
def test_ci_contract_rejects_semantic_mutants(tmp_path: Path, mutation: str) -> None:
    with pytest.raises(AssertionError):
        _assert_ci_contract(_mutated_workflows(tmp_path, mutation))


def test_ci_contract_allows_harmless_comments_and_labels(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    source = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
    text = source.read_text(encoding="utf-8").replace(
        "name: Run the full test suite", "name: Generic authority parity for Preston and Niles"
    )
    (workflows_dir / "ci.yml").write_text(
        "# Harmless authority and branch prose; no behavioral condition.\n" + text,
        encoding="utf-8",
    )

    _assert_ci_contract(workflows_dir)
