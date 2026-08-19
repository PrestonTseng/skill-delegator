# Unicorn shared event-loop latency RCA pattern

Use this reference when a Thalos/JPS REST call times out while Unicorn also serves high-rate MQTT → PubSub → GraphQL traffic. The main lesson is to test for **process-wide latency**, not assume the named REST endpoint or ADS command is slow.

## Reusable evidence chain

1. **Identify the real failing stage from source order.** A log step named for ADS notification may first call JPS for service information. Trace the call sequence and distinguish JPS HTTP timeout from ADS ACK timeout.
2. **Align client and server timestamps.** Match Mission UUID, endpoint, retry interval, and completion time. Uvicorn access logs are completion timestamps; absence of a completion before the client deadline is meaningful only when the request start is independently known.
3. **Exploit timestamps embedded in request parameters.** Poll APIs often include a freshly generated boundary such as `start_time_to`. If source confirms it is generated immediately before the request, normalize timezone and subtract it from the server completion timestamp to estimate end-to-end request latency across many samples.
4. **Build a historical same-endpoint baseline.** Compare p50/p90/p95/p99/max and count above the caller deadline. Prefer a known pre-release hour on the same Alpha host over a synthetic benchmark.
5. **Map release tags before diffing.** Several release tags may point to the same Unicorn commit. Reduce the regression interval to the actual commit range before attributing changes.
6. **Diff the endpoint implementation and shared runtime paths separately.** If REST handler/service/repository are unchanged but latency regresses, investigate shared event-loop work: PubSub fanout, GraphQL subscriptions, MQTT handlers, background jobs, serialization/copying, and cancellation cleanup.
7. **Correlate exact coroutine signatures.** `Task was destroyed but it is pending!` is useful only with the following task representation. A `coro=<Queue.get()>` line can be mapped directly to PubSub child-task creation and is stronger than a generic asyncio warning.
8. **Exclude dependency drift with source diffs, not version suspicion.** Compare changed dependency tags and pinned framework versions. A version bump that only changes logging is not a credible HTTP/DB latency cause.
9. **Quantify workload amplification.** Estimate `source update rate × (publish copy + subscriber delivery copies)` and include other high-frequency topics. This supports a hot-path hypothesis, but do not claim exact CPU attribution without profiling or controlled A/B.
10. **State confidence in layers.** Example:
   - server-side latency exceeds the client deadline: proven;
   - endpoint source did not change: proven;
   - child-task cleanup defect appears in production: proven;
   - PubSub fanout/copying is the shared regression surface: high confidence;
   - exact latency share from copying versus reconnect churn: unquantified.

## Concrete 0.21b2→0.21b5 example

Release mapping showed Unicorn b3, b4, and b5 all pointed to the same commit, so the regression interval was b2→b3.

For the same Alpha `GET /api/vehicle-mission/list/by-vehicle` path:

```text
b2: 925 samples, p95 3.349 s, max 4.146 s, 0 above 5 s
b5: 705 samples, p95 12.879 s, max 18.758 s, 193 above 5 s
```

The Vehicle-Mission REST handler, service, and repository had no source diff. The changed InMemoryPubSub path added synchronous full-payload `deepcopy()` at publish and per-subscriber delivery, plus `Queue.get()` and close-event child tasks that were cancelled without cancellation-safe draining.

Production b5 emitted 248 pending-task destruction warnings whose task representation was exactly `coro=<Queue.get()>`; the b2 baseline emitted zero. GraphQL activity also increased substantially, but logs alone could not determine whether this was initial subscriber load or reconnect churn after latency.

## Fix verification gate

Validate the candidate with the same captured MQTT rate, subscriber fanout, and concurrent REST/JPS polling:

- zero pending `Queue.get()` / close tasks after subscriber disconnect;
- no `Task was destroyed but it is pending!` warnings;
- no relevant REST request above the caller timeout;
- p95 latency comfortably below the deadline with margin;
- delivery semantics still satisfy `LATEST` freshness and `ALL` completeness.

Do not use a faster/idempotent Thalos terminate API as evidence that Unicorn is fixed. It reduces blast radius but addresses a different boundary.
