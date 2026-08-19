# SART-2028 PubSub hardening follow-up

## Context

SART-1929 RCA found that Unicorn's pre-SART-1826 `InMemoryPubSub` used latest-value storage plus binary `asyncio.Event`, with a `yield data; event.clear()` window that could erase a pending wakeup. SART-1826 changed this to per-subscriber queues and validated well for realtime vehicle `LATEST` subscribers.

Preston then asked whether the current pubsub architecture still has risks, confirmed the follow-up scope, and requested Jira SART-2028 to track hardening.

## Durable product semantics

- `LATEST` subscribers do not require every intermediate item. They require timely presentation of the latest available state.
- `ALL` subscribers require every item. Slower delivery is acceptable, but data must not be silently dropped.
- `global_notification` should subscribe to `BULLETIN_CHANGES` using `ALL`; this was previously missed.
- `LATEST` TTL/freshness policy should be subscriber-configurable. Default can be no TTL.
- Pubsub payloads should be immutable snapshots. Future code should prevent post-publish mutation from changing what subscribers receive.

## Jira ticket created

- Jira: SART-2028 — Harden Unicorn InMemoryPubSub delivery policies and observability
- Type: Task
- Assignee: Preston Tseng
- Content includes delivery policy registry, `global_notification` ALL, subscriber-level TTL, immutable snapshots, ALL slow-subscriber policy, observability, and regression tests.

## Implementation planning lesson

Before implementing SART-2028, stop for user decision on `ALL` slow-subscriber policy. The two main designs have materially different semantics:

1. Bounded queue + disconnect/raise slow subscriber when full.
   - Preserves publisher/event-loop liveness.
   - Does not silently drop `ALL` data.
   - Requires consumers to handle explicit failure/reconnect.
2. Publisher backpressure/block until `ALL` subscriber catches up.
   - Preserves every item for the subscriber.
   - A slow subscriber can stall the topic or service.

Do not choose this policy silently. Ask Preston or the system owner because it is a product/operational trade-off, not just an implementation detail.

## Test coverage to remember

- `global_notification` passes `PubSubDeliveryMode.ALL` for bulletin changes.
- `LATEST` no-TTL default replays last-known value.
- `LATEST` with TTL suppresses or marks stale last-known value according to the subscriber's configured policy.
- Post-publish mutation does not leak into delivered data or cached latest value.
- `ALL` preserves order/no-loss under rapid publishes and exercises the approved slow-subscriber policy.
- Subscriber cleanup / close behavior removes queues and does not strand waiters unexpectedly.
