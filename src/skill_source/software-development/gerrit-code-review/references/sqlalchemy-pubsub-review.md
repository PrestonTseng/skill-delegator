# SQLAlchemy + PubSub review heuristics

Use this reference when reviewing patches that convert database changes into GraphQL/WebSocket/PubSub notifications.

## Event semantics: latest-value PubSub vs operation-specific events

If a PubSub implementation stores only one latest value per topic, operation-specific events can be lost when two publishes happen before the subscriber resumes.

Review pattern:

1. Read the concrete PubSub implementation, not just the publisher/subscriber call sites.
2. Check whether `publish(topic, data)` appends to a queue or overwrites `topic -> data`.
3. Check whether `subscribe(topic)` yields every publication or only the current latest value when an event wakes.
4. If the patch changes from full-state snapshots to create/update/delete payloads, latest-value semantics are usually no longer safe: dropping intermediate full snapshots may still leave final state correct, but dropping operation-specific events loses state transitions.
5. Ask for a regression test that publishes two distinct messages back-to-back and verifies both are yielded in order.

Minimal deterministic probe shape:

```python
agen = pubsub.subscribe(topic)
first_next = asyncio.create_task(agen.__anext__())
await asyncio.sleep(0)  # let subscribe register its Event
await pubsub.publish(topic, msg1)
await pubsub.publish(topic, msg2)
got1 = await asyncio.wait_for(first_next, timeout=1)
# If got1 == msg2 and a second __anext__ times out, msg1 was overwritten.
```

## Reverse semantic drift: queue-all can break latest-state topics

The inverse fix is also risky. If a patch changes a latest-value/coalescing PubSub implementation into per-subscriber queues, verify whether the change is scoped to operation/event topics or applies globally.

Review pattern:

1. Inventory all topics using the concrete PubSub implementation, not only the Jira-mentioned topic.
2. Classify topics as either operation/event streams (must preserve every event) or latest-state streams (usually want the current snapshot, not stale intermediate snapshots).
3. For high-frequency state topics, check queue bounds. An unbounded `asyncio.Queue()` per subscriber can accumulate stale states if a WebSocket/GraphQL client is slow.
4. Prefer topic-specific policy: queue-all for event topics; coalescing or bounded/drop-oldest queues (`maxsize=1`) for latest-state topics.
5. Ask for regression tests covering both sides: rapid event-topic publishes preserve order, while rapid state-topic publishes do not build an unbounded stale backlog.

Minimal slow-subscriber sizing probe:

```python
sub = pubsub.subscribe(state_topic)
first = asyncio.create_task(anext(sub))
await asyncio.sleep(0)  # register subscriber
for i in range(1000):
    await pubsub.publish(state_topic, {"seq": i})
# Inspect implementation state if necessary, or drain with timeouts.
# Bad sign for latest-state topics: queue size grows to 1000 and first yield is seq=0.
```

Review wording:

- The requirement may be valid for one event topic while the implementation changes every topic.
- Phrase findings as a semantic regression: slow subscribers now process stale intermediate states and can create unbounded memory/logical backlog.

## SQLAlchemy `after_flush` accumulation must clear on rollback

When an event listener collects pending changes in `session.info` during `after_flush`, verify all transaction exits clear or publish the state.

Review pattern:

1. Find where `session.info[...]` is set during flush.
2. Confirm successful commit pops/clears it.
3. Confirm rollback/soft rollback also clears it; otherwise a reused Session can publish stale changes on a later commit.
4. Ask for a regression test: flush DB change -> rollback -> later commit with no relevant DB change -> assert no notification is published.

Minimal deterministic probe shape:

```python
listener._after_flush(session, None)  # stores session.info['changes']
# simulate rollback: if no rollback handler exists, info remains
listener._after_commit(session)       # later unrelated commit
# publish should not be called for rolled-back changes
```

## Review wording

Frame this as a semantic mismatch, not just an implementation detail:

- Full-list/snapshot payloads can tolerate coalescing more often because the final payload may still represent final state.
- Operation-specific create/update/delete payloads require event preservation unless the producer or consumer has an explicit reconciliation mechanism.
