# Event-driven async state-machine change planning

Use this reference when a code change coordinates two async components through state changes or events, especially when one component must reach a readiness state before another component performs an external side effect.

## Planning questions

- Which component owns the long-running lifecycle and completion semantics?
- Which component owns the side effect?
- Is the readiness state stable, or can it be invalidated by recheck/retry logic?
- Does completion already imply an event that another helper currently waits for? If yes, avoid duplicate waiting responsibilities.
- Can the desired event be missed if it fires before listener registration? Plan a subscribe-then-snapshot wait pattern.
- What cleanup must happen before the success transition?

## Recommended orchestration shape

For a stateful dependency that emits events:

```text
start/resume dependency task
→ subscribe to dependency state/event
→ snapshot current state to avoid lost wakeup
→ wait until readiness state
→ perform external side effect
→ await dependency completion when completion owns the lifecycle event
→ perform required cleanup
→ success transition
```

Keep ownership explicit:

- Dependency executor owns route/authority preparation, recheck/retry, and block-exit completion.
- Orchestrator owns mission-level side effects, success/failure transitions, and cleanup ordering.

## Test checklist

When the behavior is event-driven, test more than the happy path:

- not-ready state does not trigger the side effect;
- readiness event triggers the side effect;
- already-ready snapshot path does not hang;
- already-completed fast path behaves correctly;
- dependency failure before readiness does not perform side effects;
- side-effect failure cancels/cleans unfinished dependency work;
- cleanup runs before success transition;
- deprecated duplicate waits are not called when dependency completion already represents the event.

## Python test style

If the repository has a local mocking style exemplar, follow it. For Python multi-patch tests, prefer grouped context managers when that is the local style:

```python
with (
    patch.object(subject, "method", AsyncMock()) as mock_method,
    patch.object(subject._fsm, "transition") as mock_transition,
):
    ...
```

For async listener callbacks scheduled via `create_task`, use bounded assertion polling rather than assuming one event-loop yield is enough:

```python
async def wait_until_asserted(assertion, timeout=1.0):
    deadline = asyncio.get_running_loop().time() + timeout
    last_error = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            assertion()
            return
        except AssertionError as error:
            last_error = error
            await asyncio.sleep(0)
    if last_error:
        raise last_error
```
