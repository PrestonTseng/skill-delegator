# Thalos departing deadlock regression pattern

Use this as a reference when planning or fixing MissionExecutor/NibbleExecutor orchestration bugs in thalos.

## Problem shape

A deadlock can occur when mission-level state handling awaits a lower-level executor whose completion now depends on a later mission-level action.

Observed case:

```text
MissionExecutor._handle_departing_state()
  awaits first NibbleExecutor.execute()
NibbleExecutor.execute()
  waits for completion_future
non-terminal nibble completion
  waits for vehicle block exit
vehicle block exit
  requires departure authorization / departure signal
MissionExecutor departure authorization
  happens only after the await that is currently blocked
```

## Planning / diagnosis checklist

1. Identify whether the awaited child operation means "started/authorized" or "fully completed".
2. If child completion depends on a later parent action, do not await full completion before that parent action.
3. Prefer preserving the child executor's new semantics if they were intentional; fix orchestration at the parent boundary.
4. For thalos departure flow, model the intended ordering explicitly:
   - start/resume the first/departure nibble as an async task when it is non-terminal,
   - have `NibbleExecutor` emit `STATE_CHANGED` events for FSM transitions,
   - wait via subscribe-then-snapshot until the departure nibble reaches `AWAIT_BLOCK_EXIT`, meaning route authorization/facing-signal MA refresh has completed and the nibble is waiting for block exit,
   - only then attempt/open the departure signal,
   - await the departure nibble task completion; after SART-1848 this completion is the block-exit signal, so `MissionExecutor` should not duplicate it with a separate `_await_block_exit()` wait,
   - after first nibble `COMPLETED`, reset the departure signal to red before transitioning `DEPART_OK`,
   - cancel the task on failure before transitioning failure.
5. Treat `COMPLETED` as a fast path, not a reason to open the departure signal again. If the first nibble is already completed, reset the departure signal to red and transition `DEPART_OK` without calling `authorize_depart()`.
6. Avoid a naive one-shot permanent authority future. While a nibble is in `AWAIT_BLOCK_EXIT`, route/block/signal/TSR/bulletin changes can trigger recheck and send it back to `ROUTE_REQUEST`. Prefer the event-driven state contract (`STATE_CHANGED` plus snapshot) over exposing a misleading permanent `await_authority_ready()` API.
7. Add regression unit tests that prove:
   - departure authorization is not attempted before first nibble `AWAIT_BLOCK_EXIT`,
   - already-`AWAIT_BLOCK_EXIT` does not lost-wakeup,
   - already-`COMPLETED` skips authorization but resets departure signal and succeeds,
   - failure before readiness does not authorize departure,
   - authorization failure cancels unfinished nibble work and fails the mission,
   - reset-to-red happens before `DEPART_OK`,
   - `MissionExecutor` no longer calls `_await_block_exit()` in departing state.

## Test style and scope pitfalls

- In thalos unit tests, prefer grouped context-manager patching for mocks, matching the existing style in `test/unit_test/jps_agent_service/test__handle_websocket_message.py`:

```python
with (
    patch.object(target, "_logger") as mock_logger,
    patch.object(target, "_callback", AsyncMock()) as mock_callback,
):
    ...
```

- Do not force a full mission happy-path integration test in thalos when the test requires SS to simulate WSS behavior. If WSS simulation is not available in the repo, keep thalos coverage targeted at unit/regression boundaries and defer the end-to-end scenario to the project that owns the simulator.

## Verification used successfully

Targeted:

```bash
uv run pytest test/unit_test/mission_executor/test__handle_departing_state.py -q
uv run pytest test/unit_test/mission_executor/test__handle_nibble_executing.py -q
uv run pytest test/unit_test/nibble_executor -q
uv run pytest test/unit_test/mission_executor -q
```

Project gate:

```bash
./build.sh --run-tests
```
