# Packet-level WebSocket Stall Tracing

Use this reference when a multi-container RCA needs to determine whether a visible UI freeze is caused by backend publish/subscribe delay, WebSocket delivery, browser event-loop stalls, or component/render work.

## Pattern

Instrument the same logical packet across these seams:

1. publisher/replay before and after publish
2. broker/client receive in the backend service
3. handler start/convert/end
4. pubsub publish/set-event/done
5. subscription generator snapshot received
6. schema conversion done
7. immediately before GraphQL `yield`
8. browser raw WebSocket `message` event
9. app subscription callback
10. route/component processing
11. render observed with `requestAnimationFrame`
12. browser long-task observer

## Packet identity

Prefer an explicit packet/correlation id injected by the publisher and propagated through the service and GraphQL payload. If production payloads cannot be changed temporarily, use the best available fallback but mark it provisional:

- source CSV row id + topic + replay sequence
- message header timestamp + sequence id
- trace key + order

A repeated domain trace key is not enough for final RCA. It can validate that instrumentation works, but long runs need a unique packet id to avoid false joins when the same vehicle/position repeats.

## UI stall localization

Collect both raw WebSocket cadence and application subscription cadence.

- If raw WebSocket message gaps and subscription snapshot gaps align, the stall is upstream of component/render code.
- If WebSocket cadence is smooth but subscription callback stalls, inspect GraphQL client/Apollo/RxJS scheduling and buffering.
- If subscription callback is smooth but render is delayed, inspect component work, change detection, map rendering, and browser long tasks.

Track browser long tasks separately. Do not assume every WebSocket gap is a browser main-thread freeze; compare the long-task timestamps against the gap window.

## Analyzer output contract

For each run, write:

- joined packet timeline CSV
- stall-window JSON keyed by packet ids
- stage p50/p95/p99/max
- counts over thresholds such as >200ms, >500ms, >1s, >2s
- raw WebSocket message gap statistics
- subscription snapshot gap statistics
- render/component latency statistics
- caveats about clock domains

Within-process deltas are strongest. Cross-machine wall-clock comparisons are lower-confidence unless clocks are synchronized or the run proves offset is stable.

## Case notes from SART-1929

A first successful `/m1`, `2x`, `limit=6000` run on remote AMD64 showed:

- WebSocket gaps and subscription snapshot gaps mirrored each other.
- Component/render was fast: subscription→render p95 about 30ms, max below 100ms.
- GraphQL schema conversion was sub-ms.
- `pubsub_done → graphql_before_yield` had the largest backend-side tail and became the next suspect seam.

A failed attempt built the frontend with development config, causing the browser container to connect to `ws://localhost:8000/graphql` inside itself. For containerized browser tests, build/use config that routes through the frontend/nginx host, such as `/graphql` and `ws://${window.location.host}/graphql`.

## Coalescing vs queueing diagnostic

When a pubsub implementation stores only the latest topic value and uses a binary event/wakeup, it can coalesce intermediate realtime updates:

```text
publish A -> event set
publish B -> event already set; topic value overwritten
subscriber wakes -> sees only B
```

Symptoms look like a UI freeze followed by a jump. Backend handler and render stages may both look fast because the lost snapshots never reach the subscription callback.

Diagnostic pattern:

1. Run current semantics and count source publishes vs backend receives vs GraphQL snapshots vs raw browser WebSocket data messages.
2. Temporarily switch the pubsub seam to a queue-mode implementation that enqueues every snapshot.
3. Re-run the same Compose scenario with one variable changed.
4. If delivered snapshots rise to match publishes and browser p50/p99 gaps shrink, latest-value coalescing is a supported root-cause candidate.

Do not treat queue-mode as the production fix automatically. It is a diagnostic that changes buffering/backpressure semantics and may need bounded queues, drop policy, or rate adaptation before it is safe.

## GraphQL yield backpressure check

To test whether WebSocket/GraphQL send backpressure causes the next update stall, attach previous yield timing to the next delivered snapshot:

```text
previous_graphql_after_yield_resume_ns
previous_graphql_yield_resume_ms
```

Then correlate:

```text
current pubsub_done -> current graphql_before_yield
vs.
previous_graphql_yield_resume_ms
```

If current waits are large while the previous yield resumed quickly, and correlation is near zero, the delay is probably before or around the async iterator/resolver scheduling point, not caused directly by the previous WebSocket send await.

Next split after that result:

```text
pubsub subscriber enters wait
wait returns / event woke
snapshot read
event clear
resolver async-for receives snapshot
resolver before yield
```

This separates `event did not wake promptly` from `event woke but async generator/resolver scheduling delayed delivery`.
