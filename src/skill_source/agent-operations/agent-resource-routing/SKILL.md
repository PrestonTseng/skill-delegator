---
name: agent-resource-routing
description: Route tasks with bounded worker delegation.
version: 0.1.1
author: Preston Tseng, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [routing, delegation, context, evidence]
    related_skills: []
---

# Agent Resource Routing

Choose the smallest execution route that preserves accepted-output quality. This is a coordinator routing discipline, not delegation authority for Workers or Reviewers.

## When to Use

- A coordinator is deciding whether to work directly or isolate read-heavy context.
- A coordinator is considering two parallel work packages.
- A task prompt needs explicit resource, evidence, and stop contracts.

Do not use this Skill to let a Worker or Reviewer create agents, redesign a task graph, or expand an assigned card.

## Routing Contract

1. **Retrieve deterministically first.** Inspect the direct source, file, task, or API with the narrowest applicable tool before considering a child.
2. **Default to direct execution.** Use zero children when the work is one coherent package, the evidence fits the current context, or delegation would only restate the task.
3. **Use one read-only worker for context isolation.** Delegate only a bounded investigation whose large evidence set can be summarized without writes, user interaction, or ownership decisions. Name the context benefit before dispatch.
4. **Use two workers only for independent packages.** Both packages must be read-only, share no mutable state, require neither result to begin the other, and have separate acceptance checks. Name the latency or independent-review benefit and both packages. Otherwise use one worker or work directly.
5. **Never nest delegation.** Every child prompt must prohibit delegation, task creation, publication, merge, apply, and scope expansion. The parent agent retains synthesis and acceptance.
6. **Verify the handoff.** Check cited evidence at the source before accepting a conclusion or taking a consequential action.

Use [templates/resource-routing-card.md](templates/resource-routing-card.md) to record the decision. For a single investigation, use [templates/read-only-worker.md](templates/read-only-worker.md).

## Fast Path and Stop Discipline

- Answer routine, reversible requests directly when they need no live verification; do not create a worker, task, plan, or tool call solely for ceremony.
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

A worker stops and hands control back when the task requires a write, a user decision, credentials, shared-state coordination, a dependency outside its package, or broader scope. The coordinator then decides whether to proceed directly, revise the card, or use an already approved lifecycle route. Do not add workers to rescue a vague or blocked prompt.

## Pitfalls

- Parent-context reduction alone is not a benefit if total tokens, retries, or latency increase.
- Two related questions are not independent when one answer changes the other's method or acceptance criteria.
- A read-only worker may investigate and report; it may not implement, publish, merge, apply, or alter the task graph.
- Parallel output is not accepted until the parent agent reconciles contradictions and verifies decisive evidence.

## Verification

Before dispatch, confirm the route is `direct`, `single-worker`, or `parallel-2`; the benefit and stop conditions are explicit; every child is read-only and non-delegating; and parallel packages pass all independence checks. Afterward, confirm the parent agent verified decisive evidence and owns the final synthesis.
