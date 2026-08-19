# SART-2032 async/listener review pattern

Context: user asked for a current-diff review focused on simplification/safety, efficiency, async races, listener cleanup, and error propagation, with an explicit instruction not to modify files.

Useful review moves:

- Inspect current working tree diff and changed filenames before reading implementation.
- Read supporting primitives that control the race behavior, not just the diff: `EventEmitter`, FSM state listener dispatch, task wrappers such as `_run_nibble_executor`, and interface/base-class initialization.
- Run the narrow changed tests when possible to distinguish “tests pass” from “safe under cancellation/error interleavings”.

Findings worth remembering for similar code:

- `except Exception` does not catch `asyncio.CancelledError`; if a parent coroutine owns a child task, cancellation cleanup must usually live in an explicit `except asyncio.CancelledError` or `finally` that cancels/awaits the child and then re-raises.
- Cleanup that only awaits a child task when `not task.done()` can miss exceptions from a done task, causing unobserved task exceptions and loss of the secondary root cause.
- Event/listener waits should register the listener before checking state, remove in `finally`, and avoid fragile `Event.clear()` ordering where possible. A single Future completed by the listener can be simpler than repeated wait-task creation.
- Adding an event-emitter base class to an interface creates a safety obligation for every implementation/fake to call `super().__init__()`; consider abstract listener methods or a concrete mixin/base when reviewing future changes.
