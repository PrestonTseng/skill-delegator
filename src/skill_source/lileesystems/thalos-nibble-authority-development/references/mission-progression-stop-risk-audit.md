# Mission Progression Stop-Risk Audit

Use this reference when auditing Nibble look-ahead scheduling, route-request waits, Mission retry, or cancellation recovery before deployment.

## Route waits require phase and WSS-constraint analysis

`AuthorityContext` remains scoped to forward MA targets, while route occupancy checks apply to every controlled block. Occupancy by the mission vehicle in the current block is therefore evidence to classify, not an automatic instruction to exclude that block.

Check two distinct cases:

1. **Post-MA recheck** — the Nibble reached `AWAIT_BLOCK_EXIT`, so current-plus-forward MA was already issued. If a relevant route degrades and evaluation returns `WAIT` because the current controlled block is occupied, ADS can still exit on the existing MA and normal reconciliation can complete the Nibble.
2. **Initial entry before extension MA** — if the relevant route is genuinely unavailable while the vehicle occupies one of its controlled blocks, WSS may reject any route request until that block is free. This is a fail-safe hold. Excluding current occupancy does not create authority; it merely attempts a request expected to fail.

For either case, verify WSS's occupied-route rule, the MA currently dispatched, signal status, and the event that can end the wait. A real deadlock finding requires proof that no valid progress or reconciliation event exists. Do not weaken the occupancy gate solely to eliminate a `WAIT` result.

## Completion futures must be retry-safe

A Nibble completion future is lifecycle state, not merely an await primitive. Once it contains an exception or cancellation, every later await observes that same terminal outcome.

If retry is supported, transitioning the FSM alone is insufficient. The retry contract must ensure that the awaited completion signal represents the new attempt. Verify all of these:

- route-request failure -> retry -> eventual success;
- MA-refresh failure -> retry -> eventual success;
- block-entry timeout -> retry -> eventual success;
- departure-Nibble failure before readiness -> Mission retry;
- canceled look-ahead task -> Mission retry or explicit non-retryable handling.

Beware that canceling a task which directly awaits a bare `asyncio.Future` cancels that future. `asyncio.CancelledError` derives from `BaseException`, so `except Exception` does not catch it. A canceled nonterminal Nibble can therefore abort a later Mission state-listener task unless the completion signal is shielded, renewed, or the lifecycle is explicitly terminalized.

## Audit workflow

1. Reconstruct the actual Mission block list and route controlled-block topology.
2. Probe authority decisions for the mission vehicle occupying each current controlled block while the relevant route is `UNSET`/unauthorized.
3. Trace Mission look-ahead failure cleanup through task cancellation into Nibble completion state.
4. Trace both Nibble-level and Mission-level retry paths after exceptional and canceled completion.
5. Require focused tests that prove recovery reaches normal completion; tests that only assert cancellation/draining are insufficient.
6. Keep route/authority stop risks separate from cleanup-quality findings: a cleanly drained task can still poison future retry.

## Review reporting

For pre-deployment stop-risk audits, report each finding as a causal chain ending in the operational consequence (vehicle held, Mission stuck, retry impossible). Separate passing unit-test evidence from uncovered behavioral proof boundaries. A green suite does not clear a no-go when the stop scenario is not represented.