# Pre-Alpha Nibble Stop-Risk Audit Patterns

Use these checks when a Nibble change separates MA geometry, forward authority, route occupancy, or facing-signal ownership.

## Route-wide scope: classify before fixing

A forward-only `AuthorityContext` is not sufficient if a downstream route helper scans every `route.ctrl_block_list` entry. But an own-current-block `WAIT` is not automatically a defect.

Before proposing current-block exclusion, establish:

1. **WSS request constraint** — if WSS rejects every route containing an occupied controlled block, excluding own occupancy only sends a request expected to fail.
2. **Lifecycle phase** — in `AWAIT_BLOCK_EXIT` recheck, the Nibble has already completed `MA_REFRESH`, so current-plus-forward MA exists and ADS exit can reconcile the wait. At initial entry before extension MA, a genuinely unavailable route is a fail-safe hold.
3. **Actual release cause** — distinguish normal current-block authorization release, stale ADS reporting, route authorization degradation, and explicit Thalos revocation.
4. **Progress proof** — inspect the MA already issued, signal status, and ADS block progression. Do not infer circularity from `WAIT` alone.

A topology probe is still useful: enumerate missions and nonterminal Nibbles where the relevant route contains the current block. Follow the count with a real handler probe and record whether forward MA already exists, whether ADS exit can complete, and whether WSS would accept a request. Never recommend bypassing an occupied-route safety gate without proving the request is domain-valid.

## Facing-signal IDs are separate MA state

`set_range()` changes MA mileposts; it does not advance `facing_sig_id` or `next_facing_sig_id`. Audit every confirmed block-entry path:

- vehicle already in the Nibble block when the state handler starts;
- event-driven look-ahead entry callback;
- departure/first Nibble versus later interlocking and yard Nibbles.

A common timing bug is updating signals only on the snapshot path while the callback merely transitions to route validation. Some runs then look correct because a late-starting Nibble takes the snapshot path, while early look-ahead Nibbles retain stale IDs.

Regression test pattern:

1. put the Nibble in `AWAIT_BLOCK_ENTRY` for a later mission block;
2. deliver a real ADS status-change payload entering that block;
3. assert the MA manager receives the ordered remaining-signal list and ADS timestamp;
4. assert the FSM advances only after that update;
5. verify a mission-specific boundary where the signal pair changes, not only a first-block fixture.

When correlating logs, `Calculated facing signals` proves recalculation occurred, but absence of a decoded MA payload does not prove the exact signal IDs sent. State that evidence boundary explicitly.

## Confirmed-entry ownership across async MA updates

Adding `set_facing_signal()` to the event-driven entry callback creates a new await boundary inside `AWAIT_BLOCK_ENTRY`. Treat entry confirmation as a single-winner lifecycle event, not merely a sequence ending in a guarded transition.

Before the first await, synchronously claim block-entry processing. Then:

1. disarm the entry timer and remove the old entry listener;
2. update facing-signal IDs with the latest ADS timestamp;
3. re-check that the FSM is still in `AWAIT_BLOCK_ENTRY` before transitioning, so termination remains authoritative;
4. release the claim in `finally`;
5. make the queued timeout callback require both `AWAIT_BLOCK_ENTRY` and no active entry claim.

Why both the claim and final state check are required:

- Without the claim, a queued timeout can transition to entry-timeout error while facing-signal I/O is suspended.
- Independent ADS callback tasks can both pass the initial state predicate. Callback A may transition to `ROUTE_REQUEST`, whose handler re-registers the vehicle listener; callback B can then remove that newly registered listener during duplicate cleanup.
- The final state check prevents resurrection after termination, but by itself does not prevent duplicate I/O/cleanup side effects.

Use true-overlap tests:

- block facing-signal I/O, invoke the captured timeout callback, and prove timeout cannot commit;
- block callback A, start callback B with the same entry payload, and prove B exits before I/O/cleanup;
- assert one signal update, one cleanup, one transition, and preservation of the next state's listener;
- do not clear all `ROUTE_REQUEST` listeners unless another assertion directly proves the re-registration/removal contract, because clearing them can mask the race.

Keep this claim separate from ADS-exit/WSS-recheck arbitration: they protect different lifecycle ownership boundaries.

## FSM listener-task exception probe

The base FSM launches state listeners as background tasks. If its done callback only discards tasks, exceptions can become `Task exception was never retrieved` while the executor completion future remains pending.

For unguarded state-handler awaits:

1. inject a deterministic exception at the awaited dependency;
2. start the public executor method;
3. yield the loop and capture the loop exception handler;
4. assert FSM state, public task completion, completion-future state, and captured task exception.

Treat a nonterminal state with a pending public future as a hang even when logs contain the exception. Prefer explicit error transitions or lifecycle propagation. Keep this separate from normal-flow blockers and intentionally deferred recovery work.

## Release-gate reporting

For a stop-risk blocker, report:

- exact event ordering and operational consequence;
- one concrete mission/block/signal or route example;
- deterministic probe plus focused/full verification;
- why passing existing tests missed the path;
- live-system/HIL coverage as a residual boundary;
- known issues explicitly deferred by the owner, without silently expanding patch scope.
