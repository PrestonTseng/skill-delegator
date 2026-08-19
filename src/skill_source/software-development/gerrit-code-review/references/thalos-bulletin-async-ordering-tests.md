# Thalos Bulletin Async-Ordering Test Review

Use this note when a Thalos change claims that scheduled/effective/expired Bulletin transitions consistently recalculate a Nibble movement authority (MA).

## Coverage matrix

Test behavior and transition ordering separately:

1. Future `SCHEDULED` with a non-null future `start_time` does not clip the MA.
2. `EFFECTIVE` clips the MA.
3. `SCHEDULED -> EFFECTIVE` while already in `AWAIT_BLOCK_EXIT` triggers a refresh and sends the restricted range.
4. `EFFECTIVE -> EXPIRED` triggers a refresh and restores the unrestricted range.
5. `EFFECTIVE -> DISABLED` through API-driven revoke also triggers a refresh and restores the unrestricted range.
6. `SCHEDULED -> EFFECTIVE` during the MA-refresh critical window—after range calculation but before the refresh/listener handoff completes—cannot be lost.
7. The symmetric `EFFECTIVE -> EXPIRED/DISABLED` transition during the same critical window cannot leave the old restricted range installed.

## Deterministic race test

A useful race test must begin with a genuinely non-applicable Bulletin:

- state: `SCHEDULED`
- `start_time`: non-null and in the future
- initial calculated range: unrestricted

Block `ma_manager.set_range()` with two `asyncio.Event` objects. While blocked, transition the same Bulletin to `EFFECTIVE` through the real event-emission path (or a faithful `asyncio.create_task` equivalent), then release `set_range()`. Flush/await resulting state tasks and assert the final MA call or recalculation uses the restricted range.

Do not use `start_time=None`: production semantics may treat that scheduled Bulletin as direct-effect and already restrictive, causing a false pass.

## Listener fidelity

Thalos `EventEmitter._notify_listeners()` schedules async callbacks with `asyncio.create_task`; it does not await them. Tests that manually iterate stored callbacks and await each one impose stronger ordering than production and can hide races.

Before trusting callback injection, verify:

- production actually registers the listener in the exercised state;
- registration occurs before the transition can happen;
- callback scheduling matches `create_task` semantics;
- the assertion observes the eventual final MA, not merely the first stale `set_range()` call;
- cleanup/unregistration does not create an uncovered handoff gap.

An empty test-owned listener list is not proof of correct cleanup if production never registered a listener in that state.

## Consistency boundary and state-removal trap

Treat range calculation plus `MaManagerService.set_range()` as one consistency boundary. Re-reading ADS after the send only detects block-exit ordering; it does not detect a Bulletin generation change. A robust design either serializes Bulletin transitions with this boundary or compares a monotonic Bulletin generation/snapshot before and after the send and retries when it changed.

When requirements say ranges must recalculate when a Bulletin becomes effective **or stops being effective**, inspect relevance filters as well as range-calculation predicates. If the event handler rejects `EXPIRED`, removal cannot trigger even though expired Bulletins are excluded correctly from the calculated range. Test timer-driven `EXPIRED` and API-driven `DISABLED` independently.

Add end-to-end removal tests: begin with an effective, clipping Bulletin; transition it to `EXPIRED` or revoke it to `DISABLED`; await event/state processing; assert the MA expands to the unrestricted range.

## Focused review probe

A direct probe can establish whether the race is real:

1. Calculate the unrestricted range with a future scheduled Bulletin.
2. Enter `MA_REFRESH`.
3. Change the Bulletin to effective inside a blocked `set_range()` side effect.
4. Record the range sent and Bulletin listener-registration count.
5. Separately evaluate authority relevance for an expired Bulletin.

Use the probe as review evidence; the durable fix needs repository tests reproducing production scheduling.