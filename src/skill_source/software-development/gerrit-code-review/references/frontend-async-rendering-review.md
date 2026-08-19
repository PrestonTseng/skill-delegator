# Frontend async rendering review notes

Use this reference when reviewing UI patches that improve rendering performance by suppressing duplicate work, caching state, debouncing layout work, or deferring DOM/canvas/Konva updates through callbacks such as `Image.onload`, `requestAnimationFrame`, timers, observers, or promises.

## Review risk

Optimizations that add a `pending*`, `rendered*`, `desired*`, or duplicate-suppression flag can accidentally make an older async render complete after a newer state update. The code may pass ordinary repeated-status tests while still showing stale UI when updates arrive in a different order.

Typical failure shape:

1. Current UI is state A.
2. Update requests state B and records `pendingState = B`.
3. Before B's image/frame/timer callback runs, update requests state A or C.
4. Duplicate-suppression logic sees the old rendered state or pending state and returns early.
5. The old B callback completes and applies stale UI after the latest update.

This is especially important for realtime train/track-map displays where stale signal or vehicle state is worse than a missed optimization.

## What to inspect

- Any async callback that applies UI after state has changed: `image.onload`, `requestAnimationFrame`, `setTimeout`, `setInterval`, `ResizeObserver`, promises, subscriptions.
- Flags/attrs such as `pendingStatus`, `renderedStatus`, `currentLeft`, `animationFrameId`, or cached DOM measurements.
- Early returns that compare only the currently rendered state, not the latest desired state.
- Cleanup paths for intervals, flash images, observer listeners, and destroyed components.
- Whether stale async completions are guarded by a version/token/latest-desired-state check.

## Deterministic probe pattern

Add a temporary or permanent unit test that controls the async boundary:

```ts
// Arrange existing rendered state A.
renderInitialState(A);
flushInitialAsyncWork();

// Request state B, but do NOT flush B's async callback yet.
applyUpdate(B);

// Request newer state C before B completes.
applyUpdate(C);

// Now flush the queued async callbacks.
flushAsyncWork();

// Assert latest state C is rendered and stale B artifacts are absent.
expect(renderedState()).toBe(C);
expect(staleArtifactFor(B)).toBeNull();
```

For Jest with fake timers and mocked `Image`, queue `onload` through `setTimeout(..., 0)` and call `jest.advanceTimersByTime(0)` only after all updates have been issued.

## Fix direction

Prefer one of these designs:

- Store a per-render monotonically increasing version/token and check it inside the async callback before applying changes.
- Store a single latest desired state and have every callback compare against it before mutating DOM/canvas/Konva state.
- Cancel pending frames/timers/image work where the platform allows cancellation.
- When transitioning away from flashing/blinking states, proactively remove stale flash artifacts and clear intervals even if the base rendered state already matches the new normal color.

## Gerrit-ready wording

```text
[Medium] Async render suppression can apply stale state after a newer update
The patch records a pending state before the async render completes, but a newer update can arrive while that callback is still queued. In that case the newer update may return early because the old rendered state still matches, then the stale callback applies the older state. Please make pending renders cancellable/versioned and add tests for <state B> -> <state C> before image/frame load completion.
```
