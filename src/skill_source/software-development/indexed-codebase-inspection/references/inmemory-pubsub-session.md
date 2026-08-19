# Session reference: InMemoryPubSub event-loss inspection

## Context

A user reported that Unicorn's `InMemoryPubSub` lost operation-specific bulletin events when two `BULLETIN_CHANGES` messages were published rapidly. The old implementation stored only latest data per topic and woke subscribers via `asyncio.Event`, so rapid publishes coalesced into one wake-up.

## Codebase Memory pattern used

1. `mcp_codebase_memory_list_projects()` showed the indexed project name was `opt-data-workspace-unicorn`, not the shorter repo name `unicorn`.
2. `search_graph(query="InMemoryPubSub publish subscribe pubsub")` surfaced:
   - `src/util/pubsub/in_memory_pubsub.py` methods: `publish`, `subscribe`, helpers.
   - related consumers such as `BulletinSubscription.subscribe_bulletin_list` and `GlobalNotificationSubscription.subscribe_global_notification`.
   - producer seam `BulletinChangesListener._publish_change_notification`.
3. `search_code(pattern="BulletinChangesMessage|change_type|ChangeType|BULLETIN_CHANGES")` identified the bulletin listener/message shape and confirmed the topic usage.
4. `get_code_snippet(... include_neighbors=true)` hydrated exact producer/consumer snippets before editing.
5. `detect_changes(scope="src/util/pubsub/in_memory_pubsub.py", since="HEAD")` was used after the patch for indexed impact context.

## Durable lesson

For event/pubsub bugs, Codebase Memory helps quickly build the whole semantic picture:

- implementation under test,
- publishers,
- subscribers,
- related notification paths,
- whether other topics use state-snapshot semantics vs event-sequence semantics.

Use graph-aware search first, then read live files and run tests before finalizing.

## Fix pattern from the session

The durable implementation pattern was:

- Keep a per-topic `latest data` map for first-subscribe bootstrap semantics.
- Replace per-topic `asyncio.Event` notification with per-subscriber `asyncio.Queue`.
- On `publish`, append every message to each active subscriber queue and update latest data.
- On `subscribe`, seed the new queue with latest data if available, then yield queued messages in order.

This preserves last-known-state bootstrap while preventing active-subscriber event coalescing.
