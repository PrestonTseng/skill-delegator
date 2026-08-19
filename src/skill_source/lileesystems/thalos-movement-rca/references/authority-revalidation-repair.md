# Authority revalidation repair: implementation reference

This reference records reusable implementation and verification lessons from the July 2026 Thalos stale-Nibble repair. It supplements `stale-nibble-route-recheck.md`; exact symbols and test counts remain revision-specific.

## Responsibility model

Keep two explicitly named windows:

```text
MA calculation blocks = current confirmed block + forward extension blocks
authority target blocks = MA calculation blocks - current confirmed block
```

With an MA range of two blocks, the practical authority target is the next block. Do not infer authority responsibility from a variable called “current”; classify current entry using ADS position/confirmed block entry.

A normal WSS release of authorization for the occupied/current block is not a forward-authority degradation for that Nibble. A true `AUTHORIZED -> non-AUTHORIZED` transition on a forward block or relevant route still triggers revalidation.

## Event semantics

- Route degradation: old state is `AUTHORIZED`, new state is not.
- Block degradation: old authorization is `AUTHORIZED`, new authorization is not.
- Apply the forward authority-context filter to both route and block events.
- Ignore occupancy-only changes, unchanged states, and authorization improvements in `AWAIT_BLOCK_EXIT` recheck logic.
- Keep block/route occupancy events as `ROUTE_REQUEST` wakeups; a `WAIT` decision must be able to reevaluate when a controlled block becomes free.
- Remove `SIGNAL_STATE_CHANGED` from authority recheck/wakeup registration when signal status is derived and independently refreshed in MA dispatch.
- Preserve relevant TSR/bulletin events because they independently change usable forward authority.

## ADS listener and snapshot ordering

For both `ROUTE_REQUEST` and `MA_REFRESH`:

```text
register ADS listener
-> read ADS snapshot
-> if vehicle already left Nibble block: normal completion
-> perform awaited route/MA operation
-> read ADS snapshot again after MA work
-> if still in block: advance toward AWAIT_BLOCK_EXIT
```

During `AWAIT_BLOCK_EXIT -> RECHECK`, cleanup must preserve the ADS listener. The next state may re-register idempotently, but there must be no blind interval.

## Normal exit reconciliation

An ADS-confirmed block exit during `ROUTE_REQUEST`, `MA_REFRESH`, or `AWAIT_BLOCK_EXIT` is normal progress reconciliation:

```text
ADS exit or recheck snapshot confirms exit
-> acquire single-winner exit/recheck lock
-> recheck FSM state / transition availability
-> transition BLOCK_EXITED -> COMPLETED
-> completed-state handler cleans timers/listeners
-> completion future resolves normally after cleanup
-> Mission continues
```

The lock serializes transition commits; it does not make ADS data fresh. Do not add fixed 200/400 ms sleeps based on a nominal reporting interval.

## Terminal and malformed empty targets

- Terminal Nibble with no forward target: normal no-extension completion. Its preceding Nibble already supplied MA into the terminal block.
- Nonterminal Nibble with no forward target: retain `RouteRequestError`; silently completing would hide malformed mission/topology data and advance Mission incorrectly.

## Occupied-route guard

Before `REQUEST` or `REVOKE_AND_REQUEST`, inspect every controlled block in the route. If any is occupied, return `WAIT`. Do not rely only on occupancy within the forward authority context because WSS evaluates the whole route. Preserve `REUSE` when the route is authorized for the current mission.

## Mission integration

- Departure: first Nibble reaches `AWAIT_BLOCK_EXIT`, then authorize departure; Nibble completion means the vehicle departed the initial block, after which Mission resets departure signal and starts normal Nibble execution.
- Normal Nibble completion during validation is not a Mission fault.
- Genuine Nibble failure still propagates through ordinary error states.
- On current-Nibble failure, cancel and drain all running look-ahead tasks with `asyncio.gather(..., return_exceptions=True)` before transitioning Mission to failure.

## Minimum regression matrix

1. MA range contains current + next; authority context contains only next.
2. Current-block authorization degradation does not recheck.
3. Forward block and relevant route degradation do recheck.
4. Occupancy-only, unchanged, and improving events do not recheck.
5. Signal listeners are absent; TSR/bulletin monitoring remains.
6. ADS exit in `ROUTE_REQUEST`, `MA_REFRESH`, and `AWAIT_BLOCK_EXIT` completes normally.
7. Listener-before-snapshot and post-MA second snapshot catch movement.
8. Recheck cleanup preserves the vehicle listener.
9. ADS exit racing WSS recheck has one completion winner.
10. Occupied route returns `WAIT`, and later block/route change wakes and reevaluates it.
11. Terminal empty target completes; nonterminal empty target fails.
12. Completion future stays pending until terminal cleanup completes.
13. Departure ordering and look-ahead cancellation/draining remain correct.

Every new or materially modified Thalos test should contain explicit `# Arrange`, `# Act`, and `# Assert` comments.

## Verification sequence

```bash
uv run black --check <modified-python-files>
uv run pytest test/unit_test/nibble_executor test/unit_test/mission_executor -q
./build.sh --run-tests
git diff --check
```

After any semantic change found during review, rerun the full build. Treat a green background build as evidence only for the exact source that produced it; use a source-diff hash if edits can occur while verification runs. For Gerrit, verify the local commit, preserved `Change-Id`, current patch-set revision, status, and `Verified` label.
