from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).parents[2]
SKILL_SOURCE = REPOSITORY_ROOT / "src" / "skill_source"


def _read_skill(source: str, name: str) -> tuple[dict[str, object], str, Path]:
    path = SKILL_SOURCE / source / name / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    _, frontmatter, body = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert isinstance(metadata, dict)
    assert body.strip()
    description = metadata["description"]
    assert isinstance(description, str)
    assert len(description) <= 60
    assert description.endswith(".")
    return metadata, body, path.parent


def test_resource_routing_distinguishes_direct_helpers_and_canonical_kanban() -> None:
    metadata, body, skill_dir = _read_skill("agent-operations", "agent-resource-routing")

    assert metadata["version"] == "0.2.0"
    for term in (
        "direct",
        "single-worker",
        "parallel-2",
        "canonical-kanban",
        "representative pilot",
        "independent packages",
        "coordinator",
        "Kanban state",
        "Arena",
        "nested delegation",
    ):
        assert term in body

    reference = skill_dir / "references" / "canonical-kanban-orchestration.md"
    reference_text = reference.read_text(encoding="utf-8")
    for field in (
        "Goal",
        "Scope",
        "Context",
        "Non-goals",
        "Acceptance",
        "Verification surface",
        "Exact commands and evidence",
        "Timebox and stop",
        "Forbidden actions",
        "Report",
        "Review route",
        "Final artifact identity",
    ):
        assert field in reference_text
    for provenance in (
        "cursor/plugins",
        "0b8e952052d482ee6de06deebf14d590d77b1b34",
        "MIT",
        "Adopted",
        "Rejected",
    ):
        assert provenance in reference_text


def test_review_lifecycle_separates_verdicts_and_invalidates_stale_evidence() -> None:
    metadata, body, skill_dir = _read_skill("agent-operations", "kanban-review-lifecycle")

    assert metadata["version"] == "0.2.0"
    combined = "\n".join(
        [
            body,
            (skill_dir / "templates" / "implementation-card.md").read_text(encoding="utf-8"),
            (skill_dir / "templates" / "review-card.md").read_text(encoding="utf-8"),
        ]
    )
    for term in (
        "APPROVED | CHANGES_REQUESTED",
        "VERIFIED | NOT_VERIFIED | INCONCLUSIVE",
        "same surface",
        "stale",
        "Final artifact identity",
        "exactly one review lane",
    ):
        assert term in combined


def test_code_change_planning_requires_real_surface_proof_and_structural_controls() -> None:
    metadata, body, _ = _read_skill("software-development", "code-change-planning")

    assert metadata["version"] == "1.2.0"
    for term in (
        "real affected surface",
        "INCONCLUSIVE",
        "proxy",
        "architecture or data model",
        "type, schema, lint, or CI",
        "behavior test",
        "skill or documentation",
    ):
        assert term in body


def test_existing_grants_deliver_the_updated_canonical_ids() -> None:
    delegations = REPOSITORY_ROOT / "config" / "delegations"
    grants = {
        path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))["target"]["grants"]
        for path in delegations.glob("*.yaml")
    }

    for target in ("niles", "leo"):
        assert "agent-operations/agent-resource-routing" in grants[target]
        assert "software-development/code-change-planning" in grants[target]
    for target in (
        "niles",
        "niles-worker",
        "niles-reviewer",
        "leo",
        "leo-worker",
        "leo-reviewer",
    ):
        assert "agent-operations/kanban-review-lifecycle" in grants[target]
