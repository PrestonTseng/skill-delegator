# SART-1929 master / SART-1826 `LATEST` validation

## Lesson

When validating realtime vehicle pubsub fixes, interpret results according to the subscriber delivery mode:

- `LATEST`: completeness is not required. The acceptance question is whether the latest available state is delivered promptly once Unicorn has it.
- `ALL`: completeness is required. Slower delivery is acceptable, but every item must be delivered or an explicit failure/backpressure policy must fire.

Do not reject a `LATEST` fix solely because delivered snapshot count is lower than raw publish count. For `LATEST`, lower count can be expected coalescing.

## Source change observed

Unicorn master after `safeart-0.21b2` contained the relevant commit:

```text
06d2eee SART-1826 Fix InMemoryPubSub event delivery
```

The implementation changed from binary `asyncio.Event` fanout to per-subscriber queues:

- `LATEST`: `asyncio.Queue(maxsize=1)`, replacing stale queued values when the subscriber is behind.
- `ALL`: unbounded queue.

This removes the original `yield data; event.clear()` lost-wakeup window for `LATEST`, but still allows intentional coalescing of intermediate values.

## Validation pattern

Use the same real Crystal + remote AMD64 Docker Compose packet harness that reproduced SART-1929:

```text
route: /m1
replay: 2x
limit: 6000
Crystal: 0.21b2 e2e/instrumented frontend
Unicorn: master/SART-1826 instrumented image
```

Required checks:

1. Run image-level regression tests for pubsub behavior.
2. Confirm Mosquitto outgoing-drop log count is zero.
3. Confirm `docker compose down -v --remove-orphans` completed and no project containers remain.
4. Analyze server-local timings, especially `pubsub_done -> graphql_before_yield`.
5. Analyze browser timings, but interpret browser inter-arrival gaps against publisher/input gaps.

## SART-1929 validation result

In the SART-1929 master validation run:

```text
Master / SART-1826 pubsub_done -> graphql_before_yield:
  p50: 3.4 ms
  p95: 22.7 ms
  p99: 67.3 ms
  max: 435.0 ms
  >500 ms: 0
  >2000 ms: 0

GraphQL before-yield -> Crystal subscription received:
  p50: 8.3 ms
  p95: 37.5 ms
  p99: 103.1 ms
  max: 1064.6 ms
  >2000 ms: 0

Crystal subscription -> render:
  p50: 17 ms
  p95: 30 ms
  p99: 35.5 ms
  max: 47 ms
```

There was one browser inter-arrival gap above 2 seconds, but packet timing showed it aligned with replay/input or upstream MQTT receive timing, not Unicorn pubsub delivery:

```text
previous latest included: unicorn-recv-3500
next latest included:     unicorn-recv-3501
upstream receive gap:     ~2208.3 ms

For unicorn-recv-3501 after Unicorn had it:
  pubsub_done -> graphql_before_yield:        ~0.66 ms
  graphql_before_yield -> Crystal subscription: ~13.15 ms
```

Conclusion for this class of fix: under `LATEST` semantics, SART-1826 appears to fix the SART-1929 Unicorn pubsub lost-wakeup issue. For `ALL` subscribers, run a separate completeness test.
