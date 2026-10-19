---
name: agent-resource-routing
description: Route direct, read-only, or canonical Kanban work.
version: 0.2.0
author: Preston Tseng, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [routing, delegation, context, evidence]
    related_skills: []
---

# Agent Resource Routing

Choose the smallest execution route that preserves accepted-output quality. This is a coordinator routing discipline, not delegation authority for Workers or Reviewers, and it does not make Arena or nested delegation a default for one task.

## When to Use

- A coordinator is deciding whether to work directly or isolate read-heavy context.
- A coordinator is considering parallel read-only helpers or durable Kanban work.
- A task prompt needs explicit resource, evidence, and stop contracts.

Do not use this Skill to let a Worker or Reviewer create agents, redesign a task graph, or expand an assigned card.

## Routing Contract

1. **Retrieve deterministically first.** Inspect the direct source, file, task, or API with the narrowest applicable tool before considering a child.
2. **Default to direct execution.** Use zero children when the work is one coherent package, the evidence fits the current context, or delegation would only restate the task.
3. **Use one read-only worker for context isolation.** Delegate only a bounded investigation whose large evidence set can be summarized without writes, user interaction, or ownership decisions. Name the context benefit before dispatch.
4. **Use two read-only workers only for independent packages.** Both packages must share no mutable state, require neither result to begin the other, and have separate acceptance checks. Name the latency or independent-review benefit and both packages. Otherwise use one worker or work directly.
5. **Use canonical Kanban for durable or mutating multi-phase work.** Write an outcome-first task contract, run one representative pilot, then use rolling fan-out only for independent packages whose write ownership and acceptance checks do not overlap. The coordinator owns synthesis, acceptance, and release of later work; completion is recorded through canonical Kanban state rather than chat claims.
6. **Never nest delegation.** Every child prompt must prohibit delegation, task creation, publication, merge, apply, and scope expansion. Do not use same-task Arena competition or add workers to rescue a blocked worker. The coordinator retains synthesis and acceptance.
7. **Verify the handoff.** Check cited evidence at the source before accepting a conclusion or taking a consequential action.

Use [templates/resource-routing-card.md](templates/resource-routing-card.md) to record the decision. For a single investigation, use [templates/read-only-worker.md](templates/read-only-worker.md). For `canonical-kanban`, load [references/canonical-kanban-orchestration.md](references/canonical-kanban-orchestration.md); do not load it for direct or bounded read-only work.

## Fast Path and Stop Discipline

- Route one coherent, reversible task directly; do not create a ceremonial worker, task, plan, or tool call.
- Once prerequisites are known, make the narrowest necessary retrieval or tool call without extended pre-analysis.
- Investigate only unknowns that can materially change the answer or action.
- When acceptance criteria and proportionate verification pass, stop. Do not repeat equivalent searches or checks unless evidence conflicts, state changed, or risk requires independent validation.
- For low-impact ambiguity, state a reasonable assumption and proceed. Ask or block only when safety, authority, scope, or an irreversible choice changes.

## Evidence Contract

Each worker returns only:

- scope inspected;
- exact path and symbol or line range, URL, task ID, or other stable locator;
- material commands or retrieval operations and results;
- conclusion with confidence;
- unanswered questions and stop reason;
- a statement that no writes, nested delegation, or external actions occurred.

A claim without a checkable locator is a lead, not accepted evidence.

## Stop Rule

A worker stops and hands control back when the task requires a write, a user decision, credentials, shared-state coordination, a dependency outside its package, or broader scope. The coordinator then decides whether to proceed directly, revise the card, or use an already approved canonical Kanban route. A blocked worker stays blocked until its dependency or decision is resolved; do not add a duplicate lane or nested delegation.

## Pitfalls

- Parent-context reduction alone is not a benefit if total tokens, retries, or latency increase.
- Two related questions are not independent when one answer changes the other's method or acceptance criteria.
- A read-only worker may investigate and report; it may not implement, publish, merge, apply, or alter the task graph.
- Fan-out after a pilot is rolling, not maximal: dispatch another package only while it remains independent of active writes and the pilot has validated the contract.
- Parallel output is not accepted until the coordinator reconciles contradictions and verifies decisive evidence.

## Verification

Before dispatch, confirm the route is `direct`, `single-worker`, `parallel-2`, or `canonical-kanban`; the benefit and stop conditions are explicit; every helper is read-only and non-delegating; and every parallel package passes the independence checks. For canonical Kanban, confirm the representative pilot completed before rolling fan-out, the coordinator owns synthesis and acceptance, and completion is visible in Kanban state. Afterward, confirm decisive evidence belongs to the accepted final artifact identity.
