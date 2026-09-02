# Notification batching, durable deduplication, and package-regression review

Use this reference when a release claims secure package exclusion, configurable notification batching, or deduplication across retries/replays.

## 1. Mutation-sensitive package exclusion

A clean sdist/wheel is necessary but not sufficient. The regression must distinguish the fixed tree from the vulnerable contract.

Required proof:

1. Use fictional forbidden material only. Never read, copy, print, or hash a real ignored secret.
2. Build in a disposable project/tree whose package-selection mode deterministically selects the fictional member when explicit exclusions are removed or broken.
3. Prove RED by removing/mutating the exclusion contract; failure must identify the forbidden member in both relevant artifact types.
4. Restore the exclusion contract and prove both sdist and wheel have zero forbidden members.
5. Cover every required root/pattern (`.env`, secret roots, data, reports, caches), not only one representative filename.
6. Repeat complete archive-member scans after a fresh build; do not rely on Git ignore or Docker ignore as Python-package controls.

Pitfall: a test that builds the current repository and sees no secret can stay green because the build backend did not select the fixture even without the fix. That is artifact cleanliness, not mutation-sensitive regression evidence.

## 2. Behavioral `flush_seconds`

If configuration exposes a flush duration, changing it must change observable delivery timing—not only a batch ID or receipt hash.

A deterministic event-driven contract avoids sleeping threads:

- First queued event opens deadline `now + flush_seconds`.
- Before accepting an event at or after the deadline, flush the pending queue.
- Flush immediately at `maximum_events`.
- Preserve destination order and event order.
- Explicit close, shutdown, or run finalization flushes the remainder.
- Use an injected clock; do not use real sleeps in tests.

Required clock-controlled tests:

- Before deadline: no time-triggered flush.
- Exact deadline: flush occurs (define equality explicitly).
- After deadline: old batch flushes before the new event is accepted.
- Maximum size: early flush.
- Final close/shutdown: remaining events flush once.
- Partial failure: one destination cannot reorder or suppress healthy destinations.

Pitfall: batching an already assembled tuple proves aggregation and maximum-size chunking only. It does not prove the configured time boundary.

## 3. One deduplication authority

Single-event and batch paths must call the same destination-scoped dedup authority. Do not add a helper path that calls adapters directly.

For each candidate event:

1. Compute the canonical destination-scoped dedup identity from configured key fields.
2. Read the last successful delivery time from the durable authority.
3. Suppress when `now - prior < window_seconds`.
4. Deliver only novel eligible events.
5. Persist success only after adapter success.
6. In a mixed batch, retain duplicate receipts and deliver only novel events in stable order.
7. A failed destination must not create success state or affect another destination.

When the runtime uses short-lived manual/scheduler child processes, an in-memory dictionary cannot satisfy a rerun window. Use the system's existing durable store. If a fixed table-count contract applies, a redacted JSON column on an existing run/receipt table can preserve the count, provided writes are atomic and schema checks remain strict.

Persist only the minimum record:

- destination ID;
- deduplication ID;
- successful delivery time.

Never persist endpoint values, secret values/references, URLs, headers, payloads, raw adapter errors, or credentials in dedup state.

Post-commit rule: notification-state write failure must not roll back analytical/business evidence. Surface a bounded warning/failure receipt instead.

## 4. Cross-lifetime probes

Test all of these with an injected clock and a real temporary durable store:

- Same event twice in one router.
- Same batch twice in one router.
- Same event/batch through a new router using the same store.
- Fresh manual or scheduler child process using the same store.
- Expiry at the exact boundary and after it.
- Destination isolation.
- Mixed duplicate/new batch.
- Partial adapter failure.
- Durable-state write failure after business-state commit.
- Schema/table-count/integrity checks after delivery.

A strong release probe repeats the exact previously failing two-event batch at one clock inside the window and requires one adapter call plus a deduplicated second outcome, then repeats through a fresh process.

## 5. Review routing after a completed final-review card

A downstream review card that completes with `CHANGES_REQUESTED` is durable history; do not pretend it is still running or recreate the whole graph.

1. Inspect the current board for an existing correction/re-review lane.
2. If none exists, create one bounded correction card containing the exact findings and settled design decisions.
3. Create one dependent narrow re-review card with the original reproduction probes and zero-Critical/Important approval gate.
4. Preserve all prior passing gates and Cannot Verify boundaries.
5. Do not reopen broad review unless the correction changes architecture outside the finding boundary.
