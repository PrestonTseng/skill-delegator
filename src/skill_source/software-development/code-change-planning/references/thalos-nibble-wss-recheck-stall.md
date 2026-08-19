# Thalos Nibble WSS-Recheck Stall RCA and Fix Pattern

Use this reference when diagnosing or planning a Thalos mid-route stall after Nibble authority monitoring was added.

## Establish the running build first

Do not attribute field logs to a named release until their vocabulary matches tagged source.

For the 0.21 line:

- 0.21b2-era logs/states include `MA_REFRESHING`, `MA_REFRESHED`, `FINALIZING`, and `Vehicle ... already in block ...`.
- 0.21b3/b4 use `ROUTE_REQUEST`, `MA_REFRESH`, `AWAIT_BLOCK_EXIT`, and emit `Rechecking route authorization for nibble ...`.

If a user corrects the log date, discard conclusions drawn from the wrong window and rebuild the event timeline from the corrected source. Preserve the old conclusion only as superseded history.

## Field-confirmed race shape

The representative failure is:

```text
normal own-train overlap (next block FREE -> OCCUPIED)
-> current Nibble leaves AWAIT_BLOCK_EXIT for ROUTE_REQUEST
-> cleanup removes ADS status listener
-> ADS crosses the block boundary during revalidation
-> stale Nibble misses block exit
-> current block release removes block authorization / resets route
-> stale Nibble revokes and re-requests the old route
-> route now contains an occupied controlled block
-> WSS rejects until retry exhaustion
```

A strong timeline contains all of these, in timestamp order:

1. WSS next-block occupancy change during normal overlap.
2. `AWAIT_BLOCK_EXIT --(recheck)--> ROUTE_REQUEST` for the previous block.
3. ADS entering the next block without the previous Nibble completing.
4. Previous block `OCCUPIED -> FREE` and/or `AUTHORIZED -> UNAUTHORIZED`.
5. Stale-route revocation and route `AUTHORIZED -> CLEAR_ROUTE/UNSET`.
6. Repeated authorization timeouts while a controlled block remains occupied.
7. `ROUTE_REQUEST_ERROR` and Mission `NIBBLE_EXECUTE_ERROR`.

Vehicle-filtered logs establish Nibble behavior; all-service WSS logs establish route/block/signal ordering. Use both.

## Trigger policy

Do not use every WSS change as a route-revalidation trigger.

- **Signal:** remove signal-driven Nibble recheck and route-request wakeups. Signal state is derived from block/route state. MA dispatch may continue refreshing facing-signal status independently.
- **Block:** occupancy-only changes with unchanged authorization are normal movement and must not trigger route revalidation. Trigger only on authority degradation, and check ADS block exit first.
- **Route:** trigger on relevant `AUTHORIZED -> non-AUTHORIZED` degradation, not improving transitions into `AUTHORIZED`.
- **Bulletin/TSR:** retain relevant-range safety handling unless separately redesigned.

Do not remove all WSS monitoring; genuine block/route authority degradation still matters.

### Combined block event does not imply combined recheck semantics

Thalos WSS Agent emits occupancy and authorization changes through one `BLOCK_STATE_CHANGED` event and one payload. Keep the subscription, but separate its consumers:

- In `AWAIT_BLOCK_EXIT`, recheck only when `old_authorized == AUTHORIZED` and `new_authorized != AUTHORIZED`; occupancy-only changes return immediately.
- In `ROUTE_REQUEST`, occupancy changes still matter because they wake a Nibble waiting for an occupied controlled block to become free. Removing block occupancy monitoring globally can strand `AuthorityAction.WAIT`.

WSS commonly keeps a route block authorized while occupied, then releases authorization after `OCCUPIED -> FREE`. Therefore an `AUTHORIZED -> UNAUTHORIZED` event for the current Nibble block can be a normal post-exit release, not necessarily a new authority loss. Authorization-only filtering does not by itself resolve callback ordering.

### Serialize normal exit versus recheck

Treat normal `BLOCK_EXITED` and `RECHECK` from `AWAIT_BLOCK_EXIT` as mutually exclusive outcomes. Use one `asyncio.Lock` (or an equally explicit single-owner primitive) shared by the ADS exit callback and the WSS/bulletin recheck path. Re-read both FSM state and the latest ADS snapshot while holding that lock:

```text
acquire resolution lock
-> if state is no longer AWAIT_BLOCK_EXIT: do not issue an AWAIT transition
-> read latest ADS status
-> ADS already outside current Nibble block: cleanup and normal BLOCK_EXITED
-> ADS still inside: commit recheck, cleanup while preserving ADS listener, then RECHECK
```

Do not infer causality from ADS/WSS timestamps; transport and callback scheduling differ. Current cached ADS state at the serialization point is the decision source.

Required ordering semantics:

1. ADS cache already moved, even if its callback is delayed -> normal completion wins.
2. WSS degradation owns the lock while ADS still reports the current block -> recheck wins; movement afterward is abnormal pre-authority exit.
3. ADS callback owns the lock first -> normal completion wins; later WSS callback observes a non-`AWAIT_BLOCK_EXIT` state and returns.

Hold ownership across cleanup and transition so two callbacks cannot both clean up and issue conflicting transitions. After a waiter acquires the lock, re-check the state; do not rely on the state observed before waiting. Existing abnormal-completion idempotency should remain as defense-in-depth when an ADS event is handled after `RECHECK` enters `ROUTE_REQUEST`.

## Block-exit state semantics

Do not reuse the whole `TERMINATE` source set for `BLOCK_EXITED`.

`TERMINATE` means lifecycle cleanup is legal; it includes states such as `IDLE` and `AWAIT_BLOCK_ENTRY`, which do not prove that the vehicle entered the Nibble. Allowing exit completion there can prematurely complete a look-ahead Nibble.

Define post-entry active states explicitly:

```text
ROUTE_REQUEST
MA_REFRESH
AWAIT_BLOCK_EXIT
```

- Exit from `AWAIT_BLOCK_EXIT` is normal completion.
- Exit from `ROUTE_REQUEST` or `MA_REFRESH` before validation completes is explicit abnormal terminal completion.
- Error states require separate treatment because their completion future may already contain an exception.

Preserve ADS observation through revalidation using subscribe-then-snapshot ordering. If ADS exit wins the race, cancel the in-flight state task, clean listeners, and terminate the Nibble before any stale revoke/request can continue.

## Abnormal completion policy

For the accepted safe default:

```text
BLOCK_EXITED_BEFORE_AUTHORITY
-> COMPLETED_ABNORMAL
-> cleanup Nibble resources
-> completion raises AuthorityViolationError
-> Mission enters NIBBLE_EXECUTE_ERROR
-> Mission faults/stops
```

The critical distinction is that the Nibble must be terminal (so it cannot keep rechecking) while the movement is not reported as normal success.

### Completion-future contract

FSM state transition is synchronous, but state listeners run as background tasks. Reaching `COMPLETED_ABNORMAL` does not mean the completion future has already resolved in the same event-loop tick. The abnormal-state listener should:

1. clean runtime resources;
2. then call `completion_future.set_exception(AuthorityViolationError(...))` once.

Mission orchestration should still call `await_completion()` when it encounters a pre-existing `COMPLETED_ABNORMAL` state. That await either raises immediately if cleanup finished or waits briefly for cleanup and then raises. Skipping the await can advance the Mission before cleanup and leave the future exception unconsumed. This contract assumes executors are created in `IDLE`; if persisted-state restoration is introduced, restoration must also reconstruct or resolve the completion future.

Add a real-executor regression that blocks cleanup with an event, proves `await_completion()` remains pending, releases cleanup, and then proves it raises `AuthorityViolationError` rather than hanging.

### Mission child-task cleanup

When the current Nibble fails, cancel every running look-ahead Nibble task and await/drain all task results before transitioning Mission to failure. Cancel-without-gather can leave pending tasks or unobserved exceptions. A deterministic test should keep a look-ahead task running, fail the current task, and assert cancellation plus finalization completed before the Mission failure transition.

## Occupied-route request guard

`_get_unrelated_occupied_block()` may ignore the ADS's own current block. That is acceptable when reusing an already-authorized route owned by the current mission, but not when issuing a new request.

Required distinction:

- Route already `AUTHORIZED` by current mission + own current block occupied -> `REUSE` can remain valid.
- `REQUEST` or `REVOKE_AND_REQUEST` + any occupied controlled block, including the requesting ADS block -> `WAIT`; do not call WSS.

This guard prevents request storms but is defense-in-depth. The primary fix is preventing stale Nibbles.

## Required RED tests

1. Occupancy-only `FREE -> OCCUPIED`, authorization unchanged: remain in `AWAIT_BLOCK_EXIT`; no revoke/request.
2. Signal state change: no Nibble route recheck and no route-request wakeup.
3. Block or route authority degradation: still triggers recheck.
4. ADS exits during `ROUTE_REQUEST`: cancel work, abnormal terminal, raise `AuthorityViolationError`.
5. ADS exits during `MA_REFRESH`: same result without invalid transition or task leak.
6. Initial post-entry route validation followed by unauthorized movement: abnormal terminal and Mission fault/stop.
7. New route request containing own occupied controlled block: `WAIT`; WSS request not called.
8. Already-authorized route owned by current mission with own current block occupied: `REUSE`.
9. Full overlap ordering: prior Nibble completes, old route is not revoked by a stale Nibble, retry count stays zero.
10. ADS cache already shows the next block while a WSS degradation callback runs before the ADS callback: normal `BLOCK_EXITED` wins; no `RECHECK` or abnormal completion.
11. Concurrent ADS normal-exit and WSS degradation callbacks: exactly one cleanup and one terminal/recheck transition owns the outcome.
12. WSS degradation owns resolution while ADS still reports the current block, then ADS moves: `RECHECK` wins and the later movement follows abnormal completion without duplicate transitions.
13. Abnormal cleanup blocked by a test event: `await_completion()` stays pending until cleanup is released, then raises `AuthorityViolationError`.
14. Current Nibble failure with running look-ahead tasks: children are cancelled and drained before Mission failure transition.

Every test added or modified for this Thalos workflow must visibly follow the repository convention with explicit `# Arrange`, `# Act`, and `# Assert` comments. Do not rely on blank lines to imply phases. Keep assertions out of the Act section when practical; for expected exceptions, label the invocation as Act and retain independent postconditions under Assert.

## Verification

Run focused tests first, then the repository gate:

```bash
uv run pytest test/unit_test/nibble_executor/test_authority_recheck.py test/unit_test/nibble_executor/test_authority_validation.py -vv
uv run pytest test/unit_test/nibble_executor test/unit_test/mission_executor -q
./build.sh --run-tests
```

For Alpha validation, capture on one timeline:

- ADS current block,
- WSS block occupancy/authorization,
- WSS route state,
- Nibble FSM state,
- route request/revoke result,
- MA facing-signal ID/status.

Acceptance requires no signal- or occupancy-only recheck, immediate prior-Nibble completion on ADS block transition, no stale route churn, no occupied-route retry storm, and explicit abnormal/fault evidence if movement occurs before authority validation.

## Distinguish older departure timeout

A five-minute `DEPARTING` timeout with blank `Error during departure:` commonly reflects a string-empty `TimeoutError`. If route authorization and departure command succeeded but ADS never left the initial block, that is not evidence of the newer mid-route WSS-recheck race unless new-FSM/recheck logs are also present.
