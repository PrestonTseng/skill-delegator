# Thalos Bulletin Lifecycle / MA Race Review

Use this reference when a Thalos patch changes whether bulletins constrain movement authority, especially `NO_TRAIN_THROUGH` transitions among `SCHEDULED`, `EFFECTIVE`, `EXPIRED`, and `DISABLED`.

## Core semantic model

- `SCHEDULED` with a future `start_time`: no operational MA effect.
- `EFFECTIVE`: constrain the MA.
- `EXPIRED` or `DISABLED`: remove the constraint and recalculate affected active MAs.
- `SCHEDULED` with no `start_time` may represent direct/immediate effect in existing lifecycle code; verify the live service contract before changing it.

Checking `_get_milepost_limit()` in isolation is insufficient. Review the complete transition-to-MA path:

```text
Bulletin timer/API transition
  -> persisted/cache state mutation
  -> STATE_CHANGED publication
  -> Nibble listener registration window
  -> relevance filter
  -> route/recheck arbitration
  -> MA range calculation
  -> MaManagerService.set_range()
```

## Two mandatory race directions

### Activation race

Overlap `SCHEDULED -> EFFECTIVE` with an in-flight `MA_REFRESH`:

1. Start with a future scheduled bulletin and calculate an unrestricted range.
2. Enter real `MA_REFRESH` handling.
3. Block or intercept `set_range()` after range calculation.
4. Transition the bulletin to `EFFECTIVE` and publish the state event.
5. Release `set_range()`.
6. Assert the final MA is restricted, not merely that a helper would now return a restricted range.

A listener installed only in `AWAIT_BLOCK_EXIT` leaves a gap if `ROUTE_REQUEST` clears listeners before entering `MA_REFRESH`. An event emitted during that gap is lost unless the refresh validates a bulletin generation/snapshot after sending.

### Removal race

Run the symmetric probe for `EFFECTIVE -> EXPIRED` and `EFFECTIVE -> DISABLED`:

1. Start with a restricted range.
2. Transition while `set_range()` is in flight.
3. Assert the final MA expands/removes the bulletin constraint.
4. Verify the event relevance predicate accepts removal states. A predicate that only accepts states currently capable of applying a restriction will discard `EXPIRED`, even though expiration is exactly the event that must remove a previously applied restriction.

## Review heuristics

- Inventory where bulletin listeners are added and removed in every FSM phase: `ROUTE_REQUEST`, `MA_REFRESH`, and `AWAIT_BLOCK_EXIT`.
- Treat range calculation plus `set_range()` as a consistency boundary. Either serialize bulletin transitions with it or compare a monotonic bulletin generation/version before and after the send and retry on change.
- Re-reading ADS after `set_range()` protects block-exit ordering, not bulletin ordering.
- Event delivery through `asyncio.create_task()` is asynchronous; a unit test that directly awaits callbacks can hide real scheduling gaps.
- Do not patch over the gap by treating future `SCHEDULED` bulletins as effective early; that violates lifecycle semantics.
- Verify timer-driven transitions and API-driven revoke transitions independently.

## Minimum regression matrix

1. Future `SCHEDULED` does not clip a fresh MA.
2. `EFFECTIVE` clips a fresh MA.
3. `SCHEDULED -> EFFECTIVE` during `MA_REFRESH` leaves the final MA clipped.
4. `EFFECTIVE -> EXPIRED` during and after `MA_REFRESH` leaves the final MA unrestricted.
5. `EFFECTIVE -> DISABLED` during and after `MA_REFRESH` leaves the final MA unrestricted.
6. Irrelevant line/track/direction bulletins do not recheck.
7. Block exit racing with bulletin recheck still has one normal completion winner.
8. Tests use the real listener registration/removal and FSM transitions where possible; mocks may block I/O but must not erase the lifecycle being tested.

## Evidence wording

For a finding, report the exact lost-event interval and final sent range, for example:

```text
initial unrestricted=(...), restricted=(...)
transition=SCHEDULED->EFFECTIVE during set_range
sent=(unrestricted...), expected final=(restricted...)
listener registered during MA_REFRESH=False
```

This is stronger than saying the code “may race”: it demonstrates the stale operational MA produced by the exact patch-set revision.
