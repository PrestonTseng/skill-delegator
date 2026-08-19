# Thalos bulletin-to-MA refresh race review

Use this when a Thalos patch changes whether `NO_TRAIN_THROUGH` bulletins constrain a NibbleExecutor movement-authority range based on `SCHEDULED`, `EFFECTIVE`, `start_time`, or `end_time`.

## Core invariant

It is not enough for the range predicate to exclude future-start `SCHEDULED` bulletins. The runtime must also guarantee that a bulletin transition cannot be lost between:

1. calculating the authorized milepost range,
2. awaiting `MaManagerService.set_range()`, and
3. installing the bulletin recheck listener in `AWAIT_BLOCK_EXIT`.

`BulletinService` emits `STATE_CHANGED` asynchronously on start/end timer transitions. If the NibbleExecutor listens only after `MA_REFRESH_OK`, a `SCHEDULED -> EFFECTIVE` transition during the `set_range()` await can be missed, leaving the previously calculated unrestricted MA active.

MissionExecutor bulletin listeners do not prove this safe when they update only TSR records; verify which component owns the nibble milepost range.

## Calculation-domain parity

The lifecycle relevance predicate must inspect the same physical range as the MA calculation. Do not reuse a route-authority context without comparing its domain first. In Thalos, `_get_authorized_milepost_range()` can calculate over the current nibble block plus forward blocks, while a route context can intentionally expose forward blocks only. If lifecycle filtering uses the narrower forward-only context, a `NO_TRAIN_THROUGH` bulletin that overlaps only the current block can change the calculated MA but never increment the lifecycle revision. Both `SCHEDULED -> EFFECTIVE` and `EFFECTIVE -> EXPIRED/DISABLED` then remain stale despite an otherwise correct revision handoff.

Use one shared helper to produce the MA sub-block domain for both range calculation and Bulletin-event relevance. Add separate current-block-only activation and removal probes; assert the revision changes and the eventual final `set_range()` call has the new range.

## Deterministic race probe

Construct an overlapping `NO_TRAIN_THROUGH` bulletin with:

- state initially `SCHEDULED`,
- a non-null future `start_time`,
- an unrestricted range calculated before it becomes effective.

Pause or intercept `set_range()`. While it is in flight, change the bulletin to `EFFECTIVE` and emit the same `STATE_CHANGED` event used by `BulletinService`. Then release `set_range()` and assert the final dispatched range is clipped.

A robust implementation needs a no-lost-wakeup boundary, for example:

- arm relevant bulletin change detection before the range snapshot;
- calculate and dispatch the range;
- immediately re-read/recalculate before accepting `MA_REFRESH_OK` when a relevant change occurred;
- clean up listeners in every success, failure, and cancellation path.

Do not prescribe a particular abstraction if a small localized event/version-snapshot pattern is sufficient.

## False-pass test pattern

A test using `SCHEDULED` with `start_time=None` does **not** exercise the future-start race when production deliberately treats that state as directly effective. The range is already clipped before the simulated transition, so the test may pass even if no listener is installed and the transition event is lost.

Require the regression to prove all of the following independently:

- future non-null `start_time` leaves the initial MA unrestricted;
- transition to `EFFECTIVE` occurs during real temporal overlap with range dispatch;
- the event travels through the production-equivalent listener path;
- the final dispatched MA, not merely a helper return value, is clipped;
- listener cleanup occurs afterward.

If a test keeps its own `registered_listeners` collection, assert that the production method under test actually populated it before the transition. An empty collection plus a pre-clipped range is evidence of a false pass, not race coverage.

## Review evidence

Report separately:

- predicate/filter correctness;
- lifecycle/event correctness;
- focused tests and CI-like test results;
- deterministic race-probe result.

A green full suite does not override a failing deterministic overlap probe.