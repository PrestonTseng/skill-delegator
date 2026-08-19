# PubSub Gerrit follow-up review notes

Session-derived notes from a Unicorn `InMemoryPubSub` hardening review.

Use these when handling Gerrit comments on pub/sub, subscription, or event-delivery patches.

## Review-comment follow-up pattern

1. Read every Gerrit inline comment and classify it as blocking, accepted suggestion, rejected-with-reason, or needs-question.
2. Fix accepted comments in the smallest patch set; preserve the existing `Change-Id` with `git commit --amend`.
3. Run an explicit self-review pass on the revised diff rather than only checking the reviewer-comment lines.
4. Verify no semantic defaults remain hidden if the reviewer asked for explicitness.
5. Push the amended commit to the same Gerrit review and report the new commit SHA / patch set plus verification output.

## PubSub-specific self-review checks

- **Explicit delivery semantics:** when the design requires callers to choose between `LATEST` and `ALL`, make `delivery_mode` required in the interface and update all repo-owned `pubsub.subscribe(...)` call sites. Do not hide this in a central policy map unless the reviewer explicitly prefers that indirection.
- **AST sweep:** after changing the subscribe signature, scan source and tests for `pubsub.subscribe(...)` calls without a delivery mode. Exclude unrelated clients such as MQTT `subscribe` methods.
- **Operation-event topics:** bulletin/global notification/system severity style topics generally need `ALL`; realtime display state generally needs `LATEST`. Review every topic instead of only the Jira-mentioned one.
- **TTL clock source:** use the project/common time utility when the codebase has one, not ad-hoc `time.monotonic()` or direct wall-clock helpers, unless monotonic behavior is explicitly required and documented.
- **Immutable payload contract:** if payloads are meant to be immutable snapshots, copy at the publish boundary and document that payloads must be deepcopy-compatible. Avoid redundant per-delivery copies unless the requirement is subscriber-isolation after delivery.
- **Close semantics:** prefer an out-of-band close signal/event over mixing sentinel payloads into user data queues.

## Verification checklist

- Focused unit tests for `ALL` ordering/no replay, `LATEST` coalescing/replay, TTL stale skip, negative TTL rejection, immutable publish snapshot, logging lifecycle, and close wakeup.
- Focused subscription tests covering changed call sites/mocks after interface signature changes.
- Full local pytest where feasible.
- `py_compile` changed files.
- `git diff --check`.
- Static added-line security scan for secrets, shell injection, eval/exec, unsafe deserialization, and obvious SQL string formatting.
- AST sweep for missing explicit delivery mode after subscribe signature changes.
