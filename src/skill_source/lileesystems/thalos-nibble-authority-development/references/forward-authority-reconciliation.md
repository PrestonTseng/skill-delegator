# Forward Authority and ADS/WSS Reconciliation

## Authority Windows

A Nibble begins route validation after ADS reports entry into its current block.

- `MA blocks = current + newly covered forward blocks`
- `authority targets = MA blocks - current`

With `ma_limit_range = 2`, MA geometry uses `[current, next]`, while WSS validation targets `[next]`. Do not hard-code exactly one next block: validate every forward block covered by the configured MA range.

Routes are relevant only when their controlled-block set intersects the authority-target set.

## Recheck Rules

- Ignore normal current-block `OCCUPIED/AUTHORIZED -> FREE/UNAUTHORIZED` release for the current Nibble.
- Recheck when a forward target loses block authorization.
- Recheck when a route controlling a forward target loses authorization.
- Preserve existing TSR bulletin relevance semantics against the MA range.
- Do not use signal-only changes as authority-degradation triggers without a separately approved requirement.

## Normal ADS Reconciliation

ADS status and WSS state can arrive in different orders. If ADS reports that the vehicle is no longer in the Nibble's current block during any post-entry phase, reconcile as normal progress:

- `ROUTE_REQUEST`
- `MA_REFRESH`
- `AWAIT_BLOCK_EXIT`

All take `BLOCK_EXITED -> COMPLETED`. Do not use an abnormal Nibble state, authority-violation exception, Mission fault, or timing sleep.

Before committing a WSS-triggered recheck, snapshot ADS again. ADS exit and recheck must share single-winner arbitration. The normal `COMPLETED` handler owns runtime cleanup and completion-future resolution.

## Empty Targets

- True terminal Nibble + no forward targets: complete normally without route validation or MA extension.
- Nonterminal Nibble + no forward targets: retain route-request error behavior; do not silently classify it as terminal. This catches settings such as `ma_limit_range = 1`.

## Regression Matrix

Cover at minimum:

1. MA range contains current and next.
2. Authority context contains only forward target(s).
3. Current-block authorization release does not recheck.
4. Forward-block authorization loss does recheck.
5. Relevant forward route degradation does recheck.
6. ADS exit in route request completes normally.
7. ADS exit in MA refresh completes normally, including post-MA-operation snapshot.
8. Recheck snapshot already outside completes normally.
9. Genuine recheck while still in block returns to route request.
10. ADS exit overlaps an in-flight recheck cleanup and still completes normally.
11. Concurrent exit reconciliation transitions once.
12. Terminal empty targets complete; nonterminal empty targets fail.
13. Completion waits for centralized cleanup.

## Concurrency Test Recipe

A race regression must overlap the competing operations rather than call them sequentially:

1. Put the real FSM in `AWAIT_BLOCK_EXIT`.
2. Replace runtime cleanup with an `AsyncMock` side effect that sets `cleanup_started` and waits on `release_cleanup` only for the recheck cleanup path (`preserve_vehicle_listener=True`).
3. Start `_trigger_recheck()` as an `asyncio` task and wait for `cleanup_started`.
4. Start the ADS status callback with a payload showing the vehicle in the next block.
5. Yield once and assert the ADS task is not done while the recheck owns arbitration.
6. Release cleanup, gather both tasks, await Nibble completion, and assert normal `COMPLETED` without task exceptions.

Clear the `ROUTE_REQUEST` state listener when this test is intended to isolate arbitration; otherwise the real transition can schedule unrelated route-request work before the ADS callback acquires the lock. Keep the `COMPLETED` listener active so cleanup/future resolution remains real.

For duplicate-exit idempotency, wrap the real FSM transition with a spy. Replacing it with an inert mock prevents state change and invalidates the assertion.
