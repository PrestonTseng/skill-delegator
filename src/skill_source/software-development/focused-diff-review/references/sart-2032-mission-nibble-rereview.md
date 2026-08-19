# SART-2032 Mission/Nibble FSM Re-review Pattern

Use this as a concrete pattern when reviewing async state-machine fixes after user feedback says the code is over-complex or too edge-case-driven.

## Situation
A mission-level departing flow was fixed after a deadlock caused by awaiting a child executor's full completion before issuing departure authorization. The first fix worked, then evolved into an event-driven approach. The user challenged whether an extra helper (`_await_departure_nibble_ready`) was redundant and asked for a fresh read of both parent and child FSMs before further changes.

## Durable lesson
When reviewing an async FSM diff, do not judge helpers only by local async safety. Re-read the FSM ownership model:

- Parent/Mission FSM owns orchestration and external side effects, such as departure authorization and mission transitions.
- Child/Nibble FSM owns route/MA/readiness/block-exit state.
- A child state like `AWAIT_BLOCK_EXIT` can be the clean synchronization point if its FSM semantics already encode readiness.
- Avoid adding parent-side race helpers for theoretical child-task interleavings when the FSM model already gives a normal-state path and separate termination/error states.

## Review steps
1. Read the parent FSM state graph and the exact state handler being changed.
2. Read the child FSM state graph and identify which child state is the semantic handoff point.
3. Read the child executor implementation to confirm what that state means in practice.
4. Read the side-effect owner (for example MA manager) to confirm which module owns the operation.
5. Re-review the diff against ownership boundaries, not just against async mechanics.
6. Prefer a linear parent flow when the FSM states already encode the sequencing.

## Good outcome in this case
The final departing flow became:

```text
create readiness future
create/run departure nibble task
await readiness future
attempt departure authorization
await departure nibble completion
reset departure signal
transition DEPART_OK
```

The extra `_await_departure_nibble_ready` race helper was removed because the valuable abstraction was the readiness future/listener registration, not a second task-completion race layer.

## Pitfall
Async review can overfit to rare task races and produce defensive code that obscures the domain state machine. If the user asks for clean/maintainable code, re-ground in FSM semantics before adding more branches.