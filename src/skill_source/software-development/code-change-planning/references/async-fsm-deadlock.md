# Async FSM Deadlock Reproduction Pattern

Use this reference when an async state handler appears to hang because it awaits an operation whose completion depends on a later action in the same handler.

## Symptom

A state machine enters a state and never reaches the next side effect or transition. Logs show the handler started, but an expected downstream call never happens.

Typical shape:

```python
async def handle_state():
    await long_running_operation()  # completion depends on later side effect
    await downstream_side_effect()  # never reached
    transition(OK)
```

If `long_running_operation()` now completes only after an external event caused by `downstream_side_effect()`, the handler has a circular wait.

## Tight regression test shape

Create a test where the first awaited operation intentionally stays pending, then assert that the downstream side effect is still reached.

```python
async def test_handler_does_not_block_downstream_side_effect(executor):
    gate = asyncio.Future()
    order = []

    async def long_running_operation():
        order.append("long-start")
        await gate
        order.append("long-done")

    executor.long_running_operation = AsyncMock(side_effect=long_running_operation)
    executor.downstream_side_effect = AsyncMock(side_effect=lambda: order.append("side-effect"))

    task = asyncio.create_task(executor.handle_state(None, None))
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert order == ["long-start", "side-effect"]
    assert not task.done()

    gate.set_result(None)
    await task
```

## Fix pattern

Start the long-running operation as an owned task, perform the side effect that allows progress, then await the task before success transition.

```python
task = asyncio.create_task(long_running_operation())
try:
    await downstream_side_effect()
    await observed_external_progress()
    await task
    transition(OK)
except Exception:
    if not task.done():
        task.cancel()
    transition(FAIL)
```

## Guardrails

- Do not change the callee's completion semantics if another feature intentionally relies on them.
- Do not fire success transition until both external progress and the long-running task are complete.
- Do not leave the background task unobserved; await it or cancel/clean it on failure.
- Reuse existing task orchestration helpers if the codebase already has retry/terminal-state handling.
