# Async Orchestration Unit-Test Review

Use this reference when reviewing or simplifying unit tests for async state-machine orchestration code such as mission executors, parent/child workflow managers, or controller loops that coordinate child tasks and state transitions.

## Session-derived lesson

During SART-2032, a shared `patched_departing_flow()` context manager made the tests shorter, but the reviewer rejected it because it hid the control surface. For this class of test, the user's preferred style is: each test case should show its own grouped patches even if that repeats boilerplate.

The reason is practical maintainability:

- each test is independent
- each test shows exactly which dependencies it controls
- modifying one scenario is easier
- review is more direct for humans

## Recommended review criteria

Keep tests that map to real state-flow seams:

1. Core happy path, including meaningful intermediate ordering checks.
2. Snapshot/no-lost-wakeup path when the child FSM is already in the awaited state.
3. Fast path for an already-terminal successful state, if production code has one.
4. Failure before the readiness/authority gate.
5. Failure after readiness/authorization, including cleanup of unfinished tasks.
6. One focused event-contract test for the child emitter, rather than duplicating event details in every parent scenario.

Merge standalone tests when they only assert intermediate moments of the core happy path. Example: "not ready yet means no authorize" and "reset before success transition" can often live inside one core happy-path test.

## Preferred structure

Keep lightweight shared scaffolding:

- controllable fake child executor / fake state machine
- small async helper such as `wait_until_asserted()`

Do not hide important mocks inside a broad flow helper. Prefer explicit grouped patches in each test body:

```python
with (
    patch.object(subject, "_child_executors", [child]),
    patch.object(subject, "_authorize", AsyncMock()) as mock_authorize,
    patch.object(subject, "_cleanup", AsyncMock()) as mock_cleanup,
    patch.object(subject._fsm, "transition") as mock_transition,
):
    ...
```

This repetition is intentional. It preserves test legibility and makes each scenario self-contained.

## Pitfalls

- Do not create a broad `patched_*_flow()` helper/context manager that hides all patched dependencies.
- Do not over-split one behavior flow into many tests when a single scenario can assert the important ordering points.
- Do not add speculative edge-case tests unless the source FSM/state flow shows the scenario is possible or the user asks for it.
- Do not let fakes become complete replicas of production executors; keep them minimal and controllable.
