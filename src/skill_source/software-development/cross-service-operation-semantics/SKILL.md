---
name: cross-service-operation-semantics
description: >
  Plan or review synchronous terminal operations such as cancel, terminate, delete, revoke, and complete when a short-lived runtime executor and a durable data owner live in different services. Use for idempotency, not-found semantics, callback loops, retry amplification, caller deadlines, and minimal cross-repository fixes.
---

# Cross-Service Operation Semantics

Use this skill when a command crosses service boundaries and correctness depends on both runtime cleanup and durable user-visible state. Typical verbs are cancel, terminate, delete, revoke, complete, expire, and release.

## Core rule

**Map ownership and the existing end-to-end contract before inventing asynchronous state.**

A local executor reaching its terminal goal does not necessarily mean the durable data owner has changed. Conversely, a missing local executor may be a successful local outcome rather than an error. Success must be defined by the service that owns the user-visible truth.

## Required starting steps

1. Read the live ticket/spec and extract the exact success, timeout, retry, and idempotency requirements.
2. Inspect every participating repository from the latest approved upstream ref; do not infer a cross-service contract from one codebase.
3. Trace both directions:
   - request/command path;
   - callback, polling, subscription, or cache-observation path.
4. Identify:
   - command initiator;
   - runtime executor and its retention window;
   - durable data owner;
   - user-visible reader/UI source;
   - lock/transaction owner;
   - caller timeout;
   - each remote timeout and retry count.
5. Write the current sequence before proposing a replacement.
6. Prefer the smallest contract-preserving change that meets the requirement. Add operation resources, new states, persistence, or background task managers only when the current ownership model cannot satisfy the objective.

## Not-found semantics

Treat `not found` as a scoped result, not a universal error or universal success:

- **Short-lived runtime executor missing:** often means local cleanup is already complete or ownership aged out. Skip duplicate local transition.
- **Durable owner missing:** may satisfy a deletion/cancellation goal if absence is explicitly an accepted terminal outcome.
- **Local missing does not prove durable state:** if the current API promises durable-owner confirmation, continue that synchronization before returning success.
- **Observer event missing locally:** normally an informational no-op; do not reflexively callback the service that emitted the observation.

State which layer returned not-found and which goal it proves.

## Commands versus observations

Do not route API commands and owner-originated cache events through identical side effects unless their responsibilities truly match.

A useful source-aware split is:

- API/command source: local action plus required durable-owner synchronization.
- Owner event source: local reconciliation only; no callback to the owner.
- Duplicate event after local cleanup: informational success.

This prevents feedback loops and accidental mutations caused by bounded fetch windows or cache aging.

## Minimal synchronous idempotency

When the existing API already returns success only after the durable owner commits:

1. Re-read runtime ownership after acquiring the relevant lock.
2. Let the first caller perform the local FSM transition and remove ownership.
3. Let racing callers observe local absence and skip duplicate local work.
4. Release runtime/vehicle locks before remote HTTP.
5. Make the durable-owner command idempotent for the already-target state, preferably with an explicit FSM self-transition.
6. Avoid preflight GET-before-command when a single idempotent command can both act and confirm.
7. Propagate durable-owner timeout/5xx/non-idempotent conflicts; never return false success.
8. Use caller-level end-to-end retry after idempotency is established. A retry can skip absent local work and repeat only durable synchronization.

This often avoids tombstones, history caches, operation registries, database migrations, and new public states.

## Retry amplification review

Calculate the real worst-case path from live settings:

```text
serial duration ≈ Σ(each step's timeout × attempts + retry intervals)
```

Several individually bounded calls can exceed the caller deadline when serialized.

Prefer, when semantics allow:

- one remote attempt in the synchronous request;
- concurrent independent external steps;
- best-effort status only for steps that do not define API success;
- mandatory propagation for the durable-owner update;
- end-to-end retry instead of nested retry loops;
- path-specific changes instead of lowering global retry settings.

Never claim bounded behavior until it is compared to the actual upstream caller timeout.

## Concurrency review

Test stale-reference races explicitly:

```text
A reads executor
B reads executor
A acquires lock, transitions, removes executor
B acquires lock with stale reference
```

The implementation must re-read ownership inside the lock. If duplicate remote commands remain possible, the receiver—not an in-memory sender cache—should normally provide idempotency.

## Error contract

Separate outcomes in logs and tests:

- local action completed/already absent/failed;
- durable-owner synchronization succeeded/already target/absent/failed;
- auxiliary external cleanup succeeded/failed;
- caller result and elapsed time.

A best-effort auxiliary step may fail without changing API success only if local safety and durable user-visible state are already correct. The plan must name that boundary explicitly.

## Verification checklist

Cover at minimum:

- executor present;
- executor absent;
- owner newly reaches target state;
- owner already in target state;
- owner absent;
- owner timeout, connection failure, and 5xx;
- unrelated state conflict remains visible;
- two API callers race;
- API and observer event race;
- response lost after owner commit, then retry;
- external HTTP occurs outside the runtime ownership lock;
- elapsed time stays below the real caller deadline;
- durable state is read back before success is claimed;
- full test gates pass in every modified repository.

## Deliverable expectations

A reviewable plan should contain:

1. Current ownership and sequence.
2. Exact success/error matrix.
3. Minimal change boundaries by repository/file/method.
4. Explicit excluded complexity.
5. Test-first cases, including response-loss retry.
6. Real cross-service verification with timing and durable state read-back.
7. ADR when the API contract or ownership boundary materially changes.

For a worked TAPAS/SafeART example and the design correction that motivated this skill, read `references/tapas-mission-cancellation.md`.
