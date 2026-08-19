# SART-1929 pubsub lost-wakeup and coalescing evidence

## Context

SART-1929 investigated Crystal M1/M2/M3 realtime trackmap stalls where the vehicle appeared to pause and then jump forward after the page was left open.

The investigated path was:

```text
MQTT replay publisher
-> Mosquitto broker
-> Unicorn MQTT VehicleStatusSubscriber
-> RealtimeVehicleHandler
-> Unicorn InMemoryPubSub
-> Strawberry GraphQL subscription / WebSocket
-> Crystal Apollo subscription callback
-> M1/M2/M3 route component
-> TrackMap render
```

## Main finding

The primary supported root cause was Unicorn realtime vehicle pubsub/subscription delivery semantics, not Crystal rendering.

The important failure shape was:

```python
await event.wait()
data = latest_topic_value
yield data
event.clear()
```

This combines:

1. latest-value topic storage;
2. binary `asyncio.Event` wakeup semantics;
3. `event.clear()` after GraphQL `yield` resumes.

If a publish happens while the generator is inside `yield`, the event can be set, then cleared after the generator resumes. That erases the pending wakeup. While the subscriber sleeps, later publishes overwrite the single latest topic value.

## Observable symptom

```text
Crystal receives no vehicle snapshot for a short interval
-> TrackMap position appears frozen
-> later latest snapshot arrives
-> vehicle jumps forward
```

This can happen even when upstream MQTT updates continue and Crystal render is fast.

## Diagnostic experiments and outcomes

### Baseline event/latest-value mode

Environment:

```text
Windows AMD64
Docker Compose
Crystal /m1
2x replay
REPLAY_LIMIT=6000
```

Key observations:

```text
relevant vehicle publishes: ~4010
Crystal subscription snapshots: ~1038–1044
browser data p50 gap: 89–95 ms
browser data p99 gap: ~678–685 ms
browser max gap: 841–1549 ms across event-mode repeats
pubsub_done -> graphql_before_yield p99: ~546–564 ms
Crystal subscription -> render p95: ~29–30 ms
Crystal subscription -> render max: <100 ms in measured samples
```

Interpretation: the browser was not receiving every relevant vehicle update, but the render path was not the stall source.

### Queue-mode diagnostic

Temporary mode:

```text
SART1929_RCA_PUBSUB_QUEUE=true
```

This enqueued each publish per subscriber instead of overwriting a single latest value. It was diagnostic only.

Outcome:

```text
vehicle publishes: 4010
Crystal subscription snapshots: 4010
raw WebSocket data messages: 4010
browser p50 gap: 6 ms
browser p99 gap: ~184 ms
```

Interpretation: changing pubsub semantics alone made Crystal receive every relevant snapshot and dramatically improved browser cadence. This strongly supports pubsub coalescing/overwrite as the primary cause class.

### GraphQL yield backpressure check

Temporary fields carried previous GraphQL yield resume duration into the next snapshot.

Outcome:

```text
previous_graphql_yield_resume_ms p50/p95/p99/max: 7.0 / 49.2 / 168.4 / 597.4 ms
current pubsub_done -> graphql_before_yield p99/max: 563.5 / 1546.2 ms
correlation(current wait, previous yield duration): -0.09
```

Top current waits did not align with long previous yield durations. This weakened the hypothesis that the previous GraphQL yield/WebSocket send await directly caused the next stall.

### Clear-before-yield diagnostic

Temporary mode:

```text
SART1929_RCA_CLEAR_BEFORE_YIELD=true
```

Changed only this order:

```python
await event.wait()
data = latest_topic_value
event.clear()
yield data
```

Outcome:

```text
Crystal subscription snapshots: 1950
WS/subscription p50 gap: 23 ms
pubsub_done -> graphql_before_yield p99: 113.7 ms
pubsub_done -> subscribe wait returned p99: 90.4 ms
subscribe wait returned -> snapshot read p99: 0.0027 ms
snapshot read -> graphql_before_yield p99: 15.9 ms
```

Interpretation: clear-before-yield removed much of the event-mode server-side tail and increased delivered snapshots, proving the clear-after-yield lost-wakeup window materially contributed. It did not deliver every publish because latest-value coalescing still remained.

## Falsified or deprioritized hypotheses

- Crystal render/component bottleneck: subscription-to-render stayed below about 100 ms max in measured samples.
- GraphQL schema conversion: p99 below 0.25 ms, max below 1 ms.
- Publisher cadence: relevant publish rows had no >300 ms gaps in compared runs.
- Alpha MQTT broker drop: lab overload reproduced Mosquitto drop signatures, but Alpha incident logs did not contain that signature.
- VehicleStatusHubSubscriber as M1/M2/M3 path: source review showed M1/M2/M3 use `VehicleStatusSubscriber` / `subscribeRealtimeVehicle`; Ark Code uses `VehicleStatusHubSubscriber` / `subscribeRealtimeVehicleArkCode`.

## Production fix direction

Do not merge diagnostic queue mode as-is. It is intentionally unbounded and only proves causality.

Production should choose an explicit delivery policy:

1. bounded per-subscriber queue with drop-oldest/drop-newest/backpressure behavior;
2. sequence/drain loop until latest sequence consumed;
3. domain-aware per-vehicle latest-state batching at a display-safe cadence;
4. explicit throttle/coalesce with maximum update interval and visible skipped/coalesced metrics.

At minimum, avoid `yield data; event.clear()` lost-wakeup order. But clear-before-yield alone is not sufficient if every intermediate vehicle snapshot must be delivered.

## Regression test ideas

- Rapid-publish test with a deliberately slow subscriber: either every queued item is delivered or drops are explicit according to policy.
- Integration test across `VehicleStatusSubscriber -> InMemoryPubSub -> subscribeRealtimeVehicle` with high-frequency updates and a slow GraphQL consumer.
- Browser/Playwright replay harness acceptance: no silent snapshot loss; browser p99 close to queue-mode result; Crystal receive-to-render stays below 100 ms.

## Report-writing wording

Use precise confidence language:

```text
Primary supported root cause: Unicorn realtime vehicle pubsub/subscription delivery semantics.
High confidence that latest-value/event coalescing and clear-after-yield lost wakeup materially cause the freeze/jump symptom.
Medium confidence that clear-before-yield alone is sufficient, because latest-value coalescing remains.
```

Do not say the Alpha broker dropped MQTT messages unless Alpha logs show the Mosquitto outgoing-drop signature for the incident window.
