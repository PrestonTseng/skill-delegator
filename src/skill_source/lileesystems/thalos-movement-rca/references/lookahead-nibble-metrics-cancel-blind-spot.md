# Look-ahead Nibble Failure Hidden from Mission State

Use this pattern when an external watchdog polls the **Mission** metric and should cancel after a Nibble error, but no cancel request reaches Thalos.

## Failure shape

Thalos runs current Nibble N and one look-ahead Nibble N+1 concurrently:

```text
Mission: NIBBLE_EXECUTING
current N: ROUTE_REQUEST or AWAIT_BLOCK_EXIT       # pending
look-ahead N+1: AWAIT_BLOCK_ENTRY
90 seconds later
look-ahead N+1: AWAIT_BLOCK_ENTRY_TIMEOUT_ERROR   # failed task
Mission: still NIBBLE_EXECUTING                    # defect
watchdog: sees non-error Mission, does not cancel
```

Do not misclassify this as a Nibble-metric selection problem when the watchdog actually polls `thalos_mission_execution_state`.

## Source mechanism

`NibbleExecutor` correctly records timeout failure by setting `ExecutionTimeoutError` on its completion future. The propagation defect is in Mission look-ahead scheduling:

```python
for current in unfinished_nibbles:
    tasks[current] = create_task(run(current))
    tasks[next] = create_task(run(next))
    await tasks[current]
```

The surrounding `except` emits `NIBBLE_EXECUTE_FAIL`, but only after the **awaited** task raises. If N+1 fails while N stays pending, N+1's exception remains stored in its completed task and never reaches the Mission FSM.

The bug was introduced when sequential execution was changed to one-Nibble look-ahead scheduling. Source archaeology for the July 2026 incident identified `SART-1848 Refactor nibble FSM authorization flow` (`53f9551`) as the introducing change; always re-run blame/log on the deployed generation rather than assuming that commit is still authoritative.

## RCA procedure

1. Prove the N+1 timeout transition:

```logql
{job="containers", service_name="thalos"} |= "SERVICE_ID" |~ "TIMEOUT_ERROR|await_block_entry_timeout"
```

2. Extract the Mission FSM transitions for the complete incident. The decisive absence is:

```text
NIBBLE_EXECUTING --(nibble_execute_fail)--> NIBBLE_EXECUTE_ERROR
```

If the Mission later goes directly from `NIBBLE_EXECUTING` to `TERMINATING`, the child error never propagated.

3. Read these source boundaries in the deployed code generation:

- `MissionExecutor._handle_nibble_executing`
- `MissionExecutor._ensure_nibble_execution_task`
- `MissionExecutor._run_nibble_executor`
- `NibbleExecutor._handle_await_block_entry_timeout_error_state`
- Mission FSM `NIBBLE_EXECUTE_FAIL` transition

4. Query the expected watchdog window for the Mission UUID and distinguish endpoint invocation from internal timeout noise:

```logql
{job="containers", service_name=~"thalos|alpha-safeart-unicorn-1"} |= "MISSION_UUID"
```

Look for:

```text
thalos.api.mission_execution - Cancelling mission with mission_uuid
POST /api/vehicle-mission/<uuid>/cancel
Successfully cancelled mission with mission_uuid
```

5. Compare other successful cancels in the same minute. This distinguishes a per-Mission state-propagation defect from a global watchdog or API outage.
6. Trace later manual-mode cleanup separately; it is a different trigger and owner.

## Deterministic reproduction

At the real MissionExecutor seam:

```text
current N task: start, then await an unresolved Future
look-ahead N+1 task: raise ExecutionTimeoutError immediately
```

After N+1 fails, assert the correct contract:

- Mission handler does not remain pending;
- Mission issues exactly one `NIBBLE_EXECUTE_FAIL`;
- pending sibling tasks are canceled and drained;
- no `Task exception was never retrieved` warning remains.

The defective signature is:

```text
lookahead_task_done=True
lookahead_exception=ExecutionTimeoutError(...)
mission_handler_done=False
mission_transitions=[]
```

Existing tests commonly cover only the opposite direction—current N fails and N+1 is canceled. Audit for the missing inverse case.

## Repair contract

Preserve one-Nibble look-ahead while supervising both tasks:

1. Normal N completion advances N+1 to become current without restarting it.
2. Exception from N or N+1 immediately propagates to Mission.
3. On failure, cancel and `gather(..., return_exceptions=True)` all pending siblings before Mission transition.
4. Emit exactly one `NIBBLE_EXECUTE_FAIL`.
5. Mission metric must become `NIBBLE_EXECUTE_ERROR` in time for the next watchdog poll.

A `FIRST_EXCEPTION` substitution must be reviewed carefully: when N completes normally while N+1 remains pending, some wait APIs behave like `ALL_COMPLETED`. A safe implementation waits for current completion **or** any supervised child failure, then explicitly inspects completed tasks for exceptions.

## Interpretation

- N+1 timeout + Mission remains `NIBBLE_EXECUTING` + no cancel-start marker: task error did not propagate; watchdog correctly skipped the Mission.
- Mission enters `NIBBLE_EXECUTE_ERROR` + no cancel-start marker: investigate watchdog query/filter/execution.
- Cancel-start marker exists + no terminal result: investigate Thalos endpoint execution.
- Thalos cancel succeeds and JPS returns HTTP 200: cancellation path worked; attribute the trigger correctly.
