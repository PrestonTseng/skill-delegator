# PubSub immutable snapshot review notes

Use when reviewing pub/sub delivery-semantics patches that claim immutable payload behavior, snapshot delivery, queue fanout, or latest-value replay hardening.

## Lesson

A single `deepcopy()` at publish time protects against the publisher mutating the payload after `publish()`, but it does **not** automatically protect subscribers from each other or protect future `LATEST` replay from a consumer mutating the object it received.

Check all mutation boundaries:

1. **Publisher boundary** — publishing code should snapshot or otherwise freeze the payload before storing or enqueueing it.
2. **Fanout boundary** — active subscribers should not receive the same mutable object reference when one subscriber could mutate it before another consumes it.
3. **Replay boundary** — cached latest values should not be replayed as a mutable reference that a prior subscriber already touched.
4. **Delivery contract** — if the implementation relies on frozen DTOs instead of copying, verify the DTOs are actually immutable at nested fields too.

## Deterministic probes

Run small probes against the exact reviewed patch set in addition to normal tests.

### LATEST replay consumer-mutation probe

```python
import asyncio
from util.pubsub.in_memory_pubsub import InMemoryPubSub
from util.pubsub.base import PubSubDeliveryMode

async def anext_timeout(gen):
    return await asyncio.wait_for(anext(gen), timeout=1)

async def main():
    pubsub = InMemoryPubSub()
    await pubsub.publish("topic", {"nested": {"value": 1}})

    first = pubsub.subscribe("topic", delivery_mode=PubSubDeliveryMode.LATEST)
    received_first = await anext_timeout(first)
    received_first["nested"]["value"] = 99
    await first.aclose()

    second = pubsub.subscribe("topic", delivery_mode=PubSubDeliveryMode.LATEST)
    received_second = await anext_timeout(second)
    print(received_second)
    await second.aclose()

asyncio.run(main())
```

If output is `{'nested': {'value': 99}}`, consumer mutation leaked into cached replay.

### ALL fanout consumer-mutation probe

```python
import asyncio
from util.pubsub.in_memory_pubsub import InMemoryPubSub
from util.pubsub.base import PubSubDeliveryMode

async def anext_timeout(gen):
    return await asyncio.wait_for(anext(gen), timeout=1)

async def main():
    pubsub = InMemoryPubSub()
    s1 = pubsub.subscribe("topic", delivery_mode=PubSubDeliveryMode.ALL)
    s2 = pubsub.subscribe("topic", delivery_mode=PubSubDeliveryMode.ALL)
    t1 = asyncio.create_task(anext_timeout(s1))
    t2 = asyncio.create_task(anext_timeout(s2))
    await asyncio.sleep(0)

    await pubsub.publish("topic", {"nested": {"value": 1}})
    r1 = await t1
    r1["nested"]["value"] = 99
    r2 = await t2
    print(r2)
    await s1.aclose(); await s2.aclose()

asyncio.run(main())
```

If output is `{'nested': {'value': 99}}`, one subscriber can mutate another subscriber's queued object.

## Review wording

When this fails, phrase it as a subscriber-boundary gap rather than saying the patch lacks snapshotting entirely: the implementation may have solved publisher mutation but still fail consumer-side isolation.
