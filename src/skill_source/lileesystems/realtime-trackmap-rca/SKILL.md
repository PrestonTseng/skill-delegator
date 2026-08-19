---
name: realtime-trackmap-rca
description: Investigate SafeART/TAPAS realtime trackmap stalls across MQTT broker, Unicorn pubsub/GraphQL subscriptions, Crystal WebSocket/Apollo receive, route components, and render. Use for SART-style reports where vehicle updates appear delayed, bursty, coalesced, or frozen/jumpy.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [lilee, safeart, tapas, rca, trackmap, mqtt, graphql, crystal, unicorn]
---

# Realtime Trackmap RCA

## When to use

Use this skill when investigating realtime trackmap or subscription delay in SafeART/TAPAS, especially paths like:

```text
ADS/WSS/MQTT capture -> MQTT broker -> Unicorn subscriber/handler -> InMemoryPubSub -> GraphQL subscription/WebSocket -> Crystal -> M1/M2/M3/TrackMap render
```

Trigger phrases include:
- Crystal M1/M2/M3 trackmap freezes, jumps, or accumulates delay;
- WebSocket messages arrive in bursts;
- MQTT replay vs browser timing does not line up;
- frontend render is suspected but backend subscription delivery has not been proven clean;
- SART RCA reports involving realtime vehicle status.

## Operating principles

1. **Use broker-mediated replay first when broker/client behavior is in scope.** Direct handler replay is useful only after the broker boundary is characterized.
2. **Run the real Crystal page before clearing the frontend.** Backend-only or headless GraphQL success does not prove browser/Apollo/component/render behavior is clean.
3. **Trace every boundary with per-packet timestamps.** Aggregate p95/p99 alone can hide coalescing and lost wakeups.
4. **Compare one variable at a time.** Event-mode vs queue-mode, clear-after-yield vs clear-before-yield, hub enabled vs disabled, or route M1-only vs M1/M2/M3 should each be isolated.
5. **Separate production evidence from stress-envelope evidence.** Synthetic replay overload or broker drops are not Alpha RCA when Alpha incident logs do not show the same signature.
6. **Temporary instrumentation is not a product fix.** Diagnostic queue-mode and tracing fields must not be merged as-is.

## Required pipeline timestamps

Collect enough data to join this chain:

```text
publisher before/after publish
-> broker/client receive
-> Unicorn MQTT callback received
-> RealtimeVehicleHandler start/end
-> pubsub publish done
-> pubsub subscriber wait return / snapshot read / event clear
-> GraphQL resolver before yield / after yield resume
-> browser WebSocket message
-> Apollo subscription callback
-> M1/M2/M3 component processed
-> TrackMap ngOnChanges
-> render observed after requestAnimationFrame
```

Use `Date.now()`/epoch timestamps for cross-process joins and `performance.now()` for browser-local deltas.

## RCA interpretation checklist

- Raw capture or publisher cadence already has gaps -> upstream/source/capture path.
- Publisher cadence is clean but Unicorn MQTT receive gaps appear -> broker/client/backpressure boundary.
- Unicorn receive/handler are clean but subscription delivery loses snapshots -> inspect pubsub semantics and GraphQL subscription iterator.
- GraphQL/Crystal receive is delayed but Crystal receive->render is fast -> backend/subscription delivery, not render.
- Crystal receive->render or long tasks exceed thresholds -> then investigate Angular/component/render performance.
- Queue-mode delivers every packet while event/latest-value mode does not -> baseline pubsub is coalescing/overwriting updates.
- Clear-before-yield improves event-mode delivery -> current `yield data; event.clear()` likely has a lost-wakeup window.

## Shared event-loop latency affecting REST/JPS

Use the same pipeline RCA when Thalos/JPS REST calls time out while Unicorn is under MQTT/PubSub/GraphQL load; the visible failure may be outside the trackmap even though the shared runtime pressure originates in the realtime path.

- Trace the source call order first: a step named `Notify ADS` may actually block on a preceding JPS service-info GET, so classify JPS HTTP and ADS ACK separately.
- Uvicorn access logs mark completion, not request start. Align them with a client timestamp, or with a source-verified fresh timestamp embedded in a query parameter, before calculating latency.
- Compare the same endpoint against a known pre-release Alpha baseline and count requests above the caller deadline; do not infer a stall from sparse access-log gaps alone.
- Map release tags to commits before diffing. If several tags are identical, narrow the regression interval to the actual changed release.
- Diff the REST handler/service/repository separately from shared runtime paths. An unchanged endpoint with degraded latency points toward event-loop work, PubSub fanout, subscriber churn, background jobs, serialization, or DB/runtime contention.
- For asyncio warnings, capture the task representation after the warning. Map an exact coroutine such as `Queue.get()` back to the code that creates it; a generic `Task was destroyed` count is insufficient.
- Quantify synchronous fanout work as source rate × payload size × subscriber copies, but label exact CPU attribution unproven until profiling or controlled A/B confirms it.
- Keep blast-radius mitigation separate from root-cause repair: bounded/idempotent Thalos termination can protect callers while Unicorn still needs its own performance/task-lifecycle fix.

See `references/unicorn-shared-event-loop-latency.md` for the b2/b5 comparison method, coroutine-signature evidence, confidence ladder, and candidate verification gate.

## Pubsub lost-wakeup/coalescing pattern

Watch for this async-generator shape:

```python
await event.wait()
data = latest_topic_value
yield data
event.clear()
```

Failure mode:

```text
publish happens during GraphQL yield/send
-> event is set
-> generator resumes
-> event.clear() erases the pending wakeup
-> subscriber sleeps until a later publish
-> latest-value store overwrites intermediate snapshots
```

Symptoms:
- Crystal receives far fewer subscription snapshots than relevant MQTT/Unicorn vehicle publishes;
- trackmap appears paused then jumps to a later vehicle position;
- backend handler and Crystal render timings remain fast;
- queue-mode or sequence-drain diagnostics dramatically increase delivered snapshots.

See `references/sart1929-pubsub-lost-wakeup.md` for the concrete SART-1929 evidence and report-writing pattern.

## Production fix guidance

Do not recommend an unbounded queue as the production answer. Prefer one of:

1. bounded per-subscriber queue with explicit drop/backpressure policy;
2. monotonically increasing sequence plus drain loop until latest sequence consumed;
3. domain-aware per-vehicle latest-state batching on a fixed display cadence;
4. explicit throttle/coalesce policy with a maximum update interval and observable skipped/coalesced counts.

Preston's SART-2028 design decisions for Unicorn pubsub hardening:
- `global_notification` must subscribe to `BULLETIN_CHANGES` with `ALL`; this was a missed semantic requirement in the SART-1826 follow-up.
- `LATEST` TTL/freshness policy is subscriber-level, and the default may be no TTL. Do not impose a global TTL without asking.
- Pubsub payloads should be immutable snapshots. If mutable Python objects are still passed, enforce or verify snapshot semantics at the publish boundary so post-publish mutation cannot leak to subscribers.
- `ALL` means every item matters: slower delivery is acceptable, but silent drop is not. Any bounded-queue policy must choose explicit backpressure, disconnect/error, or another visible operational behavior.

Minimum instrumentation for the fix:
- publish count;
- delivered count;
- coalesced/skipped count;
- lost sequence count;
- queue depth / subscriber lag p95/p99/max;
- GraphQL/WebSocket send lag;
- Crystal receive->render latency.

## Confluence RCA reporting

When asked to write an RCA page:
- first inspect sibling RCA reports under the same parent and mirror their human-facing structure before writing; for SART RCA pages this usually means `Reported by`, `Bug Ticket`, TOC, `TL;DR`, `Issue`, `Root Cause Analysis`, `Reproduce / Validation Steps`, and `Repair Suggestions`;
- preserve original tester observations as process evidence, but separate them from final root-cause conclusions;
- write for human readers first and AI/search second: lead with where the gap/failure is located, then the proof, then the root cause and repair direction;
- prefer diagrams and visual summaries over large tables for timing-gap localization, e.g. pipeline boundary diagrams, publish-vs-delivered bar summaries, and sequence diagrams for lost wakeups;
- keep detailed metrics, long hypothesis matrices, and raw evidence in an appendix/expand rather than the main narrative;
- include an evidence/falsification matrix with status controls only when it helps; do not let it dominate the page;
- explicitly list what is not the RCA;
- use careful confidence language: “primary supported root cause” rather than “only cause” when residual tails remain;
- report diagnostic modes as evidence, not production patches.

See `references/sart1929-human-readable-rca-format.md` for the SART-1929 rewrite lesson and diagram patterns.

## Verifying pubsub fixes against SART-1929

When validating a post-RCA pubsub implementation change:
- for Preston visual checks, start from a quick source-overlay build on the remote Windows RCA host if the reviewed source is local and a compatible Unicorn image already exists; do not spend many tool calls fighting Docker Desktop credential-helper/registry pull issues unless the CI image itself is the thing under test;
- replay captured MQTT in chronological order (`capture_time` ascending, CSV id secondary) and use `speed=1` for natural M1/M2/M3 visual confirmation unless a stress speed is explicitly requested;
- if vehicle motion appears reversed or unnatural, check replay ordering before investigating Crystal render or pubsub behavior;
- do not stop at source inspection; rerun the same real Crystal + Docker Compose packet harness that reproduced the issue;
- compare against the known baselines: event/latest-value `~1038–1044 / 4010` Crystal snapshots, diagnostic queue-mode `4010 / 4010`, clear-before-yield `1950 / 4010`;
- distinguish fixing the `yield data; event.clear()` lost-wakeup window from fixing latest-value coalescing. A `Queue(maxsize=1)` `LATEST` implementation removes the clear-after-yield event window but can still replace stale queued values for slow subscribers;
- interpret pass/fail by delivery mode, not raw snapshot count alone:
  - `LATEST` does **not** require complete delivery of every intermediate update; it requires timely display of the latest available state. Validate freshness from Unicorn publish/pubsub to GraphQL/Crystal, and explain expected coalescing.
  - `ALL` requires every item; slower delivery is acceptable, but drops require explicit failure/backpressure policy.
- when a browser inter-arrival gap remains, compare it to publisher/input and Unicorn MQTT receive gaps before blaming pubsub. A >2s browser gap can be upstream if Unicorn also had no new vehicle input during that interval.
- accept the fix only if the observed behavior matches the product's delivery policy: either all intended snapshots are delivered, or drops/coalescing are explicit, bounded, and visible via metrics.

## Related reference

- `references/sart1929-pubsub-lost-wakeup.md` — concrete SART-1929 finding: Unicorn `InMemoryPubSub` latest-value/event coalescing plus clear-after-yield lost wakeup.
- `references/sart1929-human-readable-rca-format.md` — human-first SART RCA page structure and visual diagram patterns learned from Preston's feedback.
- `references/sart1929-master-sart1826-latest-validation.md` — validation pattern and result for Unicorn master/SART-1826 queue semantics under `LATEST` vs `ALL` delivery expectations.
- `references/sart2028-pubsub-hardening.md` — follow-up hardening scope and Preston decisions: `global_notification` uses `ALL`, subscriber-level `LATEST` TTL default no TTL, immutable payload snapshots, and `ALL` slow-subscriber policy decision gate.
- `references/remote-windows-visual-replay.md` — quick path for remote Windows M1/M2/M3 visual validation: copy local source and build an overlay image over an existing compatible Unicorn image before spending time on registry/Docker Desktop credential-helper workarounds.
