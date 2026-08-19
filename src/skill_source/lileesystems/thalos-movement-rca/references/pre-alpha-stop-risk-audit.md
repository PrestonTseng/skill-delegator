# Pre-Alpha vehicle-stop risk audit

Use this bounded audit after a movement-authority repair is complete but before advising a field/Alpha run. It is a reusable gate, not a substitute for real ADS/WSS E2E evidence.

## Audit scope

Trace every path that can intentionally or accidentally withhold movement:

1. Nibble `AWAIT_BLOCK_ENTRY -> ROUTE_REQUEST -> MA_REFRESH -> AWAIT_BLOCK_EXIT -> COMPLETED`.
2. Mission departure Nibble, departure authorization, departure-signal reset, and normal Nibble look-ahead.
3. Route `REUSE`, `REQUEST`, `REVOKE_AND_REQUEST`, and `WAIT` decisions.
4. WSS route/block degradation and occupancy wakeups.
5. ADS exit snapshots and callback races during route/MA work.
6. Listener/timer cleanup and completion-future ownership.
7. Terminal block and malformed empty-forward-target handling.
8. Genuine failure cleanup, especially cancellation/draining of look-ahead tasks.

Keep findings causal: report a concrete sequence from event/state to withheld MA, route churn, timeout, or Mission failure. Do not elevate general style suggestions into Alpha blockers.

## Static topology probe

Across every configured mission:

- detect repeated block IDs when range selection uses `.index(current_block)`;
- verify each current/forward MA window is ordered and bounded;
- ensure every controlled forward target maps to an expected mission route;
- print the exact target mission’s block-by-block MA, authority, and route sequence;
- verify terminal Nibbles alone have an empty forward target.

Repeated blocks are not automatically a bug, but they invalidate a first-index range implementation and require occurrence-aware identity.

## Deterministic runtime probes

### Race stress

Repeat the highest-risk tests many times, not once:

- ADS exit during authority validation;
- ADS exit while recheck cleanup is deliberately blocked;
- concurrent exit callbacks.

A genuine concurrency test must hold one task with events, start the competing task while the first remains suspended, then release it. Sequentially awaiting both paths is not a race test.

### WAIT wakeup

Drive the real route-handler loop through:

```text
forward/controlled block occupied
-> authority decision WAIT
-> handler remains pending
-> WSS block/route event marks it releasable
-> wakeup future resolves
-> reevaluation requests/reuses route
-> FSM reaches MA_REFRESH
```

Testing listener registration and `AuthorityAction.WAIT` separately does not prove this end-to-end handler behavior.

### Departure/look-ahead

Verify:

```text
first Nibble reaches AWAIT_BLOCK_EXIT
-> departure is authorized
-> first Nibble completes on departure
-> departure signal resets
-> current and one look-ahead Nibble run
```

On genuine failure, sibling tasks must be cancelled and drained before Mission failure transition.

## Evidence integrity

- Confirm repository HEAD and clean working tree before and after probes.
- Remove temporary probe tests and re-check cleanliness.
- Run focused Nibble/Mission suites on the final source.
- A full build completed before review edits is stale evidence. Rerun it, or prove source identity with a diff hash captured before and after.
- Query Gerrit and compare current patch-set revision with local HEAD; record `Verified` status separately from code-review approval.

## Go/no-go wording

A **go** means no concrete code/runtime stop-risk was found within the reviewed scope and the exact candidate revision passed its gates. It does not claim all field risks are impossible.

For Alpha, monitor at least:

- ADS block transition timestamps;
- Nibble state transitions;
- WSS block occupancy/authorization changes;
- route request/revoke activity and owner;
- MA range/facing-signal updates;
- timeout/fault transitions.

Issue **no-go** when a reproducible path can leave a Nibble waiting without a wakeup, revoke/request an occupied route during normal progress, lose ADS exit reconciliation, produce an empty nonterminal authority target, or fault Mission before child cleanup completes.
