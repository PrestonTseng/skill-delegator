# FSM orchestration review pattern

Use this reference when reviewing a diff that coordinates two or more FSM/executor flows, especially async code that waits for state-change events.

## Session lesson

A departing-flow review initially focused on possible async races inside a helper that waited for a nibble executor to become ready. After re-reading both Mission and Nibble FSMs, the cleaner conclusion was that the helper was mostly redundant: the normal state-flow invariant already supplied the right synchronization point.

## Review method

1. Read every relevant FSM transition table, not just the changed executor method.
2. Write down each actor's ownership:
   - Which FSM owns readiness?
   - Which FSM owns side effects?
   - Which FSM owns termination/cancellation cleanup?
3. Identify the intended normal sequence before reviewing edge cases.
4. Ask whether a defensive branch duplicates an invariant already guaranteed by another FSM.
5. Prefer a linear await sequence when the FSM semantics are already strong enough.
6. Keep edge-case branches only when there is evidence the normal invariant can be violated in production.

## Concrete shape

For a mission/departure-style flow, the clean structure is often:

```text
create state-readiness future/listener
start child executor task
await readiness state
perform parent-owned side effect
await child completion
perform parent-owned cleanup/reset
transition parent FSM
```

Avoid adding a second helper that races readiness against child task completion unless the child task can legitimately complete before the readiness state and the parent has a meaningful non-error action in that case.

## Review smell

If a helper's purpose is hard to explain without listing several theoretical branches, re-check the FSMs first. The helper may be compensating for uncertainty rather than modeling a real state-flow requirement.
