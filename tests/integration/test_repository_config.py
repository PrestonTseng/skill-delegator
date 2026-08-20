from pathlib import Path

import yaml

from skill_delegator.config import load_config

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_checked_out_repository_config_validates() -> None:
    load_config(REPOSITORY_ROOT / "config")


def test_ci_runs_the_same_branch_agnostic_repository_gates_on_linux_and_macos() -> None:
    workflow_path = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    forbidden_fragments = (
        "origin/main",
        "git archive",
        "github.ref",
        "github.head_ref",
        "github.base_ref",
        "refs/heads/",
        "git branch",
        "skillctl lock",
        "skillctl apply",
        "skillctl verify",
        "skillctl status",
        "authority",
        "generic",
        "parity",
        "niles",
        "leo",
        "preston",
    )
    lowered = workflow_text.lower()
    assert not [fragment for fragment in forbidden_fragments if fragment in lowered]

    expected_gates = [
        "uv run --frozen --python 3.12 pytest -q",
        "uv run --frozen --python 3.12 ruff format --check .",
        "uv run --frozen --python 3.12 ruff check .",
        "uv run --frozen --python 3.12 python -m compileall -q src tests",
        "uv run --frozen --python 3.12 pytest -q tests/integration/test_schema_artifacts.py",
        "uv build --python 3.12",
    ]
    jobs = workflow["jobs"]
    assert {job["runs-on"] for job in jobs.values()} == {"ubuntu-latest", "macos-latest"}
    for job in jobs.values():
        assert "if" not in job
        assert not [step for step in job["steps"] if "if" in step or "working-directory" in step]
        checkout = next(
            step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")
        )
        assert "with" not in checkout
        assert [step["run"] for step in job["steps"] if "run" in step] == [
            "uv sync --locked --python 3.12",
            *expected_gates,
        ]
