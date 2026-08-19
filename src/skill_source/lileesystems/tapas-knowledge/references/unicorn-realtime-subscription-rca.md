# Unicorn realtime subscription RCA pattern

Use this reference when investigating TAPAS realtime track-map latency, especially the path:

```text
ADS / WSS -> MQTT broker -> Unicorn MQTT subscribers -> InMemoryPubSub -> GraphQL subscription -> Crystal
```

This captures the reusable debugging method and findings from the SART-1929 Unicorn RCA session. It is not a permanent claim about Alpha/production behavior; use it as a reproduction and measurement pattern.

## Key lessons

- Do not infer backend queue backlog from repeated vehicle rows in a GraphQL subscription log.
- Unicorn realtime vehicle subscription sends a current vehicle snapshot/list. If one vehicle updates, unchanged vehicles may still appear again in the emitted snapshot.
- For Unicorn `safeart-0.21b2`, `InMemoryPubSub` was latest-state/event based rather than an unbounded queue-all mechanism. Intermediate events can be coalesced if a subscriber has not consumed the previous notification.
- A raw MQTT capture must be analyzed separately from Unicorn output. In the SART-1929 capture, `/v1/obs/status/+` vehicle positions were stable at ~200ms and had almost no duplicate positions, even though frontend-side logs had suggested repeated positions.
- To validate user-visible stalls, measure all boundaries instead of only final subscription receive time.

## Four-stage timing model

Instrument or log these timestamps with a trace key that can be joined across stages:

1. MQTT replay/publisher timestamp: before/after broker publish.
2. Unicorn MQTT received timestamp: inside the MQTT subscriber callback.
3. Unicorn internal publish timestamp: before/after `pubsub.publish(...)` after conversion/aggregation.
4. GraphQL subscription received timestamp: in a headless websocket subscription client.

Suggested trace key for vehicle status rows:

```text
<vehicle_id>|<milepost>|<block_id>|<sub_block_id>|<lane_id>
```

When GraphQL output omits some raw fields, use a partial key cautiously, e.g. vehicle + milepost. Mark unmatched or ambiguous joins explicitly.

## Replay approach

- Start a real local MQTT broker (Mosquitto is enough) and publish the captured CSV through the broker instead of directly invoking handlers. This tests broker/client behavior too.
- Use a streaming CSV parser; do not load large MQTT captures into memory.
- Replay at real time first when possible; accelerated replay is useful for stress but must be labelled.
- Subscribe to GraphQL with a headless client; do not rely on Crystal rendering when isolating backend timing.
- Preserve artifacts under the task directory:
  - publish timing JSONL
  - subscription timing JSONL
  - Unicorn logs with instrumentation
  - joined timing analysis

## Useful evidence to report

- Raw MQTT per-topic and per-vehicle cadence.
- Raw vehicle effective position-change intervals and duplicate streaks.
- Publish -> Unicorn receive latency.
- Unicorn receive -> pubsub publish latency.
- Lock wait / conversion / pubsub publish internal breakdown.
- Pubsub publish -> subscription receive latency.
- Websocket subscription message interval distribution.
- Count of raw vehicle updates vs GraphQL subscription messages.

## Pitfalls

- Full-snapshot subscription output can make unchanged vehicle positions look like duplicate source data.
- Latest-state/coalescing pubsub means missing one-to-one correspondence between MQTT updates and subscription messages is not automatically a bug.
- A single local headless subscriber may not reproduce Alpha stalls. If local replay is clean, test slow subscribers, multiple subscribers, production-like resource limits, or gather Unicorn-side timestamps in Alpha.
- Do not treat one ambiguous joined outlier as proof of queued delay when matching keys are partial or coalesced events are expected.
