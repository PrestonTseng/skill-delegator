# Async State Ownership Review Notes

Use this when reviewing or adjusting FSM/async orchestration where a side effect could reasonably live in more than one state handler.

## Lesson

Do not judge side-effect placement only by ordering. Also ask which state semantically owns the effect.

In the SART-2032 Thalos departing/departed review, `MissionExecutor` needed to avoid duplicate departure-signal reset. A technically valid ordering was:

```text
DEPARTING: authorize departure → await departure nibble completion → reset departure signal → DEPART_OK
```

The reviewer preferred the cleaner state ownership:

```text
DEPARTING: authorize departure → await departure nibble completion → DEPART_OK
DEPARTED: reset departure signal → NIBBLE_EXECUTE
```

This kept the reset associated with the `DEPARTED` semantic phase instead of overloading `DEPARTING` with post-departure cleanup.

## Review heuristic

When a state transition moves from state A to state B and a side effect happens at the boundary:

1. Confirm the required ordering.
2. Identify which state semantically owns the side effect.
3. Avoid doing the same side effect in both states.
4. Update tests on both sides of the boundary:
   - State A test asserts the side effect is **not** performed there.
   - State B test asserts the side effect is performed before the next transition.

## Test pattern

Prefer explicit per-test grouped patches so the state boundary is visible:

```python
with (
    patch.object(executor, "_reset_departure_signal", AsyncMock()) as mock_reset,
    patch.object(executor._fsm, "transition", Mock(side_effect=transition)) as mock_transition,
):
    await executor._handle_departed_state(None, None)

mock_reset.assert_awaited_once()
mock_transition.assert_called_once_with(MissionTransitionEnum.NIBBLE_EXECUTE)
assert order == ["reset", MissionTransitionEnum.NIBBLE_EXECUTE]
```

## Pitfall

A patch can be logically correct but semantically noisy if a cleanup action is placed in the preceding active state just because that is where the awaited operation completes. For human reviewability, prefer state-owner semantics when ordering remains correct.
