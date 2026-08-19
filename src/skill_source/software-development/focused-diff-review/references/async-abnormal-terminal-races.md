# Async abnormal-terminal race review

Use this pattern when an executor monitors external state while awaiting authority, I/O, or another state machine.

## Three-point observation boundary

1. Register the external listener before reading state.
2. Read an initial snapshot and stop immediately if the terminal event already occurred.
3. After the final awaited authority/I/O operation, read a second snapshot immediately before the success transition.

The third check matters because the external tracker may update while its callback remains queued behind the completing state task. If no `await` occurs between the final snapshot and transition, the success boundary is atomic with respect to the event loop.

## Concurrent terminal callbacks

Cleanup often awaits retries or remote operations. Claim terminalization before the first cleanup await with a state transition, lock, or dedicated in-progress flag. Otherwise two callbacks can both enter cleanup and attempt the same FSM transition. A duplicate caller should return without issuing another transition.

## Error-terminal orchestration

An abnormal terminal state is terminal for the child lifecycle but not equivalent to success. Review every parent path that classifies child states:

- unfinished-work filters;
- terminal fast paths;
- restart/recovery paths;
- readiness futures used by departure/startup orchestration;
- cancellation/drain logic for child tasks.

Those paths must await or re-raise the stored completion failure. Merely adding the abnormal state to a generic terminal-state set can silently filter it out and let the parent continue.

## Compatibility

When FSM states are persisted, serialized, emitted, or represented by `IntEnum`, append new values rather than inserting them among existing members. This preserves existing numeric values.

## Focused tests

- Listener is registered before the initial snapshot.
- External state changes during the final awaited operation; the final snapshot yields abnormal completion, not success.
- Two concurrent terminal callbacks produce one cleanup and one transition.
- A pre-existing abnormal child state faults the parent rather than being filtered as completed.
- A readiness future receives the abnormal failure and cannot hang.
- Existing enum values remain stable when the enum is externally observable.
