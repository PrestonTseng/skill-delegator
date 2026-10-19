# Canonical Kanban orchestration

Load this reference only when durable, mutating, or multi-phase work requires canonical Kanban. Keep one coherent reversible task direct, and keep bounded read-only context isolation on the helper routes in the main Skill.

## Outcome-first task contract

Write these fields before releasing work. Prefer observable outcomes over prescribed implementation details.

- **Goal:** the user-visible or system outcome that must exist.
- **Scope:** exact repositories, paths, systems, and operations authorized.
- **Context:** known state, dependencies, decisions, and stable evidence locators.
- **Non-goals:** adjacent work explicitly excluded.
- **Acceptance:** checkable scenarios and required end state.
- **Verification surface:** the real runtime, UI, integration, or artifact surface where the outcome must be reproduced and verified; state why it is unavailable when applicable.
- **Exact commands and evidence:** commands or retrievals to run, expected exit semantics, stable locators, and material outputs to retain.
- **Timebox and stop:** budget, completion stop, escalation threshold, and conditions that block rather than broaden the task.
- **Forbidden actions:** writes, targets, publication, merge, deployment, credentials, delegation, or graph changes outside granted authority.
- **Report:** changed files or artifacts, commands and exit codes, findings, concerns, assumptions, and recommended next action.
- **Review route:** exactly `none`, `same_card`, or `child:<id>`, consistent with the existing graph.
- **Final artifact identity:** exact commit SHA or head plus tree, or immutable artifact digest to which all evidence and verdicts bind.

A task is ready only when every applicable field is concrete enough that completion can be accepted from evidence rather than narrative confidence.

## Pilot and rolling fan-out

1. Select one representative pilot that exercises the complete task contract, including the verification and reporting surfaces. Do not choose the easiest outlier.
2. Complete and accept the pilot before releasing more packages. Repair the contract first if the pilot exposes ambiguity.
3. Fan out only packages that are independent in prerequisites, mutable state, ownership, and acceptance checks. If one result changes another package's method, sequence them.
4. Use rolling fan-out: release another independent package only when capacity is available and the accepted pilot still represents it. Do not maximize concurrency by default.
5. Keep synthesis and acceptance with the coordinator. Workers report evidence and canonical Kanban state records completion; chat claims do not release dependencies.

If a worker blocks, preserve the block and resolve its named dependency or decision. Do not create a duplicate lane, same-task Arena, or nested delegation to route around it.

## Completion and stop discipline

- Stop a package when its acceptance and required verification pass on its Final artifact identity.
- Stop and block when authority, credentials, a user decision, an unavailable dependency, identity drift, or shared-state conflict prevents valid completion.
- Mark unavailable required real-surface proof `INCONCLUSIVE`; proxy checks are supporting evidence, not a substitute.
- When the Final artifact identity changes, treat prior verification and review evidence as stale and rerun the required checks.
- Complete, block, or request the one configured review transition through canonical Kanban. Do not create a second review lane.

## Provenance and decisions

Source inspiration: `cursor/plugins` at inspected commit `0b8e952052d482ee6de06deebf14d590d77b1b34`, licensed MIT. This reference synthesizes process concepts and does not copy large upstream passages.

**Adopted:** outcome-first contracts, a representative pilot before fan-out, rolling concurrency for independent packages, coordinator-owned synthesis and acceptance, explicit evidence and stop contracts, and durable completion state.

**Rejected:** Cursor-specific plugin wiring and commands; wholesale plugin import; default same-task Arena competition; nested delegation or swarms; worker-owned graph redesign; hidden inheritance; new runtime skill identities; and autonomous merge, publication, deployment, apply, credential, or cross-container authority. These conflict with the existing canonical IDs, grants, role boundaries, or least-authority model.

## Verification

Before release, confirm the contract contains every field above, the representative pilot is named, later packages meet every independence condition, and exactly one Review route matches the graph. At acceptance, confirm the coordinator inspected the report, decisive evidence binds to the Final artifact identity, and canonical Kanban state—not a conversational assertion—records the result.
