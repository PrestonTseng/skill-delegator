# Asyncio Shared-Runtime Latency Pattern

This reference captures a reusable diagnostic pattern from a Unicorn/JPS release regression. It is not a permanent claim that every JPS timeout has the same cause.

## Symptom pattern

- A REST endpoint is unchanged between releases.
- Caller timeouts increase sharply while server requests still eventually complete successfully.
- Other APIs in the same process slow at the same time.
- GraphQL/WebSocket subscriber churn increases.
- Asyncio reports destroyed pending tasks naming a concrete coroutine such as `Queue.get()`.

The key shift is to investigate the shared event loop and subscription runtime, not only the slow REST handler or SQL query.

## Comparable latency reconstruction

When access logs do not include request duration but the request contains a caller-generated timestamp:

1. verify what that parameter timestamp represents;
2. pair it with the server completion timestamp;
3. use the same method for baseline and incident windows;
4. compute sample count, percentiles, max, and count above the caller deadline;
5. state that this is caller-start-to-server-completion latency, not pure handler CPU time.

A server 200 after the caller deadline supports timeout/retry behavior but does not prove the exact caller exception without raw client evidence.

## Release isolation

Map every product release to the exact component revision. A later product build may carry the same component commit as the first bad build. Locate the first changed component release before diffing.

Check separately:

- failing REST handler/service/repository;
- shared PubSub/subscription code;
- MQTT handlers and full-state aggregation;
- runtime dependency pins;
- internal shared libraries.

An unchanged endpoint plus a changed PubSub runtime is evidence for process-wide pressure, not proof by itself.

## Deep-copy fanout estimate

For a publish path that copies a full snapshot once at publish and once per subscriber delivery:

```text
copies_per_second ≈ publish_rate × (1 + subscriber_count)
```

Use measured update rate, measured subscriber count, and representative payload size. Treat the result as workload estimation until CPU/event-loop profiling measures actual cost.

Look for:

- `copy.deepcopy()` or serialization inside the event loop;
- full-state snapshots published on every item update;
- copy work repeated once per subscriber;
- increasing payload size over time;
- synchronous transformation before each GraphQL yield.

## Child-task lifecycle proof

For subscriber code that creates child tasks around waits:

```python
queue_get_task = asyncio.create_task(queue.get())
close_task = asyncio.create_task(close_event.wait())
```

verify all exits:

- normal message delivery;
- close-event completion;
- cancellation before publish;
- cancellation during yield/send;
- generator close;
- PubSub shutdown;
- repeated reconnect.

Cancellation is not complete when `task.cancel()` is called. Pending children must be awaited/drained, normally from a `finally` path using a cancellation-safe gather with `return_exceptions=True`.

A production error naming `Queue.get()` is strong source matching only after confirming the changed code is what creates that child coroutine in the affected process.

## One-variable A/B matrix

Hold the capture, replay rate, subscriber fanout, endpoint polling, and environment constant. Compare:

1. known-good baseline;
2. current bad revision;
3. task-cleanup-only candidate;
4. copy-path-only candidate;
5. combined candidate.

Collect:

- endpoint p50/p95/p99/max and deadline exceedances;
- event-loop lag;
- CPU profile aligned to UTC;
- task count and pending-task destruction warnings;
- publish/delivered/coalesced/dropped counts;
- subscriber count and reconnect count;
- payload size and copy/serialization duration.

Set acceptance before testing. A typical deadline-sensitive criterion is zero requests above the client timeout plus a documented p95 safety margin, not merely a lower average.

## Evidence boundaries

The following can be proven independently:

- server-side latency regression;
- no source change in the slow endpoint;
- changed shared-runtime implementation;
- orphaned child-task defect;
- high copy/fanout workload estimate.

The exact percentage of latency caused by copy CPU versus reconnect churn remains unquantified until profiling or one-variable A/B separates them.
