---
name: code-change-planning
description: Plan-first workflow for user-approved code changes before editing, testing, committing, or pushing.
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [planning, code-change, approval, workflow, user-preference]
    related_skills: [test-driven-development, systematic-debugging, gerrit-code-review]
---

# Code Change Planning

Use this whenever the user asks to modify code, fix a bug, add tests, amend a patch, or push a code change.

## Required user approval gate

Before editing any production or test code for this user:

1. Inspect enough context to understand the current state and likely scope.
2. Present a concrete plan that includes:
   - files/classes/functions expected to change,
   - intended behavior change,
   - test strategy and expected failing test, when applicable,
   - commit/Gerrit strategy if the work will be submitted.
3. Discuss and adjust the plan with the user.
4. Wait for explicit approval such as "同意", "照這個做", or equivalent.
5. Only then edit code.

Do not treat a high-confidence fix as permission to modify code. Approval is part of the workflow.

## Execution after approval

- For bug fixes and behavior changes, follow TDD: write or adjust the failing test first, run it red, then implement.
- Keep the scope aligned to the approved plan. If investigation reveals a material scope change, stop and present an updated plan before continuing.
- Verify with targeted tests and formatting checks before commit/push.
- Summarize real command output, not intended results.

## Repository maturity / source-of-truth refactors

When a user says a repository feels like a POC, review pack, or migration dump and asks to turn it into a long-lived source-of-truth/code-generation project, use `references/source-of-truth-repository-maturity.md`. It covers path classification, small authored bundles compiled into one immutable model, generator seams, Git artifact policy, compatibility questions, KISS structure, and the design-approval sequence.

For this user, default to **current-responsibility structure**: do not pre-create extension directories, target/profile hierarchies, nested subpackages, console/app shells, or migration/review archives. Add a directory only when the approved change adds a real maintained file and responsibility there. Remove one-time migration/review code after parity/evidence is secured unless a continuing maintenance use is named. “Single source of truth” neither requires one giant file nor justifies a speculative framework.

For safety-adjacent control/code-generation plans, use `references/safety-critical-codegen-plan-review.md`. It covers deep immutability, complete contracts, semantic legacy migration with a human-approved fingerprint, exact-runtime address probes, atomic command framing, centralized resource ownership, fail-closed active-state behavior, semantic/runtime verification, grouped artifact rollback, and re-approval after material review changes.

When asking this user to approve a safety-scope delta, explain it in plain language before asking for the decision: what the system knows, what it cannot know, the conservative behavior, the benefit, and the operational cost. Use a concrete analogy where helpful; do not present enum/state-machine vocabulary without translation.

## Async FSM / await-order deadlocks

When planning a fix for an async state handler that hangs before a later side effect, use `references/async-fsm-deadlock.md`. The regression test should keep the first awaited operation pending and assert that the downstream side effect is still reached; the fix should own the long-running operation as a task, perform the enabling side effect, then await/cancel the task safely.

For event-driven async state-machine changes, use `references/event-driven-async-state-machine.md`. It covers subscribe-then-snapshot waits, readiness-vs-completion ownership, cleanup ordering, rigorous edge-case tests, and project-local grouped `with (patch.object, ...)` mock style.

For the thalos MissionExecutor/NibbleExecutor departure variant, also use `references/thalos-departing-deadlock.md`. It captures the SART-1848 completion-semantics pitfall, the preferred mission-level orchestration shape, and the test-scope constraint that full mission happy-path integration tests should be deferred when SS cannot simulate WSS behavior.

For Thalos mid-route stalls involving normal block overlap, route auto-reset, or WSS route/block/signal monitoring, use `references/thalos-nibble-wss-recheck-stall.md`. It covers release verification by log vocabulary, the stale-Nibble block-exit race, the own-occupied-block policy mismatch, and the required decision plus async regression probes. For this class of fix, treat signal state as a derived result of block/route state rather than a route-revalidation trigger; distinguish post-block-entry states from the broader `TERMINATE` source set; and if ADS exits before authority validation finishes, terminally clean up the Nibble as an explicit abnormal completion before faulting/stopping the Mission.

## Pitfalls

- Do not say "I'll change X" and then edit without approval.
- Do not bundle unrelated cleanup into an approved bug fix.
- Do not skip the red test just because the fix is obvious.
- Do not push to Gerrit until commit contents and verification are complete.
- Do not fix async FSM deadlocks by reverting a callee's new completion semantics when other orchestration already relies on those semantics; plan a local orchestration fix first.
- If the user changes scope mid-execution or says to stop a branch of work, stop that branch immediately, update the durable task record, and continue only with the still-approved scope.
- Before proposing integration tests, verify that the repository can simulate or control every required external subsystem. If a requested happy-path test depends on unavailable simulators, defer it to the appropriate project instead of forcing a brittle mock-heavy integration test.
- Reviewer feedback is not user approval. If an internal grill materially removes behavior, narrows proof scope, or changes fail-safe transitions from an approved design, mark the revised plan non-executable and reopen the user approval gate before implementation.
- Do not ask a non-specialist to approve safety semantics using only state-machine jargon. First translate the decision into observable behavior, uncertainty, conservative response, benefit, and operational cost.
