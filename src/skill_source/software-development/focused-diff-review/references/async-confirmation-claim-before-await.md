# Claim Confirmed Events Before Awaiting

Use this pattern when an async callback confirms a lifecycle event (entry, readiness, completion, ownership) while a timeout, duplicate callback, or termination can compete.

## Failure shape

A callback observes a confirmed event, then awaits I/O before it disarms the old state's timer/listener or claims ownership. During that await:

- a queued timeout can transition to an error state despite confirmation;
- a duplicate callback can run the same cleanup;
- callback A can transition and the next state can re-register a listener, then callback B can remove that newly registered listener;
- termination can win, after which the callback may incorrectly revive the old flow.

A final `if state == EXPECTED` guard prevents only the last invalid transition. It does not prevent duplicate side effects or removal of next-state resources.

## Review invariant

Before the first await, the confirmed-event path must synchronously establish a single winner with one of:

- a state transition into an explicit processing state;
- a boolean claim owned by the lifecycle object;
- a lock/atomic claim whose acquisition semantics do not leave the old timeout active.

Then:

1. disarm the old timer and remove old-state listeners;
2. perform required awaited I/O;
3. re-check state immediately before the success transition so termination remains authoritative;
4. release the claim in `finally`;
5. make queued timeout callbacks check both current state and the claim before transitioning.

Do not reuse a completion/exit lock when the ownership concept is different unless its name and invariant genuinely cover both paths.

## True-overlap tests

Use barriers/events rather than sequential calls.

### Timeout overlap

1. start confirmed-event handling;
2. block the awaited I/O on an event;
3. invoke the captured/queued timeout callback while I/O is blocked;
4. assert the state remains in the confirmed-event source state and the handler remains pending;
5. release I/O and assert exactly one success transition.

### Duplicate callback overlap

1. start callback A and block its awaited I/O;
2. start callback B with the same qualifying payload;
3. assert B exits without entering I/O or cleanup;
4. release A;
5. assert one I/O call, one cleanup, one transition, and preservation of any listener registered by the next state.

### Termination overlap

1. block confirmed-event I/O;
2. terminate the lifecycle object;
3. release I/O;
4. assert the callback does not transition out of the terminal state or re-register old-state resources.

## Review warning signs

- Timer/listener cleanup appears only after a network/MA/database await.
- A state guard exists only after cleanup, suggesting side effects can still duplicate.
- Tests clear the next state's listeners, masking listener re-registration/removal races.
- A race test awaits callback A to completion before invoking callback B.
- A generic lock is present, but the competing path does not acquire or consult it.
