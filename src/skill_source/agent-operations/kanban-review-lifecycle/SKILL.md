---
name: kanban-review-lifecycle
description: Choose the correct Kanban review transition by role.
version: 0.1.0
author: Preston Tseng, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kanban, review, lifecycle, evidence]
    related_skills: []
---

# Kanban Review Lifecycle

Select one review lane and one terminal transition for each assigned card. This Skill explains role boundaries; it does not grant delegation, graph redesign, merge, publication, deployment, or apply authority.

## When to Use

- A coordinator writes an implementation or review card.
- A Worker is ready to choose the card's terminal transition.
- A Reviewer must report a same-card or separate-child verdict.
- An existing review child could otherwise cause a duplicate review lane.

## Required Route

Every implementation card must contain exactly one literal field:

`Review route: none | same_card | child:<id>`

Before work and again before the terminal transition, inspect the assigned card, its comments, attachments, parents, and children. If the route is missing, malformed, or inconsistent with the existing graph, stop and return the discrepancy to the coordinator; do not invent or repair the lifecycle.

## Role Procedure

### Coordinator

1. Choose the route before implementation begins.
2. For `child:<id>`, create and link the one review child before releasing implementation, and record the exact child ID on both cards.
3. Own correction routing after a separate-child `CHANGES_REQUESTED` verdict. Workers and Reviewers do not create replacement lanes or rewire dependencies.

### Worker

After implementation and fresh verification:

- `none` → complete the implementation card with evidence.
- `same_card` → request same-card review once with evidence.
- `child:<id>` → confirm that exact pre-created child depends on the implementation card, then complete the parent to release it. Do not request same-card review.

On retry, inspect the current route and children again. Never infer that a prior review transition should be repeated.

Use [templates/implementation-card.md](templates/implementation-card.md) for the required fields.

### Reviewer

- **Same-card review:** approve by completing the reviewed card; request changes on that card with actionable evidence when blocking findings remain.
- **Separate review child:** complete the child itself with an explicit `APPROVED` or `CHANGES_REQUESTED` verdict, severity counts, and evidence. Never request changes against the completed implementation parent and never create another review lane.

A separate-child `CHANGES_REQUESTED` verdict reports findings only. The coordinator decides whether and how implementation is requeued. Use [templates/review-card.md](templates/review-card.md).

## Minimum Evidence Ladder

1. Pin the exact task, commit or artifact identity, and authorized scope.
2. Inspect the complete diff or deliverable, including untracked in-scope files.
3. Run the required focused and regression verification against that same identity.
4. Recheck scope, prohibited side effects, and final identity.
5. Record commands, exit codes, material results, concerns, and the recommended next action.

Do not mark a card successful from confidence, an earlier run, or another agent's summary alone.

## Pitfalls

- An existing child is a graph fact, not a suggestion to add same-card review.
- `kanban_request_review` and a pre-created review child are alternative lanes, not cumulative gates.
- A separate Reviewer reports a verdict on its own child; it does not mutate the completed parent.
- Review approval does not imply merge, publication, deployment, apply, or credential authority.

## Verification

Before the terminal transition, state the exact route, role, chosen operation, and why the other operations are excluded. Confirm the recorded evidence belongs to the final inspected identity and that no second review lane was created.
