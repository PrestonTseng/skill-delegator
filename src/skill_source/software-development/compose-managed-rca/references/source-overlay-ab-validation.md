# Source-overlay A/B validation for event-loop and PubSub fixes

Use this pattern when a candidate changes only application source, the target playground already has the exact release image, and a fresh dependency-resolving build is blocked or would add unrelated variables.

## Evidence question

Compare the stock release image with the candidate under one identical retained workload. For event-loop/PubSub fixes, collect both direct hot-path evidence and a concurrent latency-sensitive endpoint:

- retained MQTT input count and replay speed;
- stable GraphQL/WebSocket subscriber count;
- controlled subscriber connect/disconnect churn;
- REST/JPS request p50/p95/p99/max and counts above the caller timeout;
- application CPU/memory samples;
- `Task was destroyed but it is pending!` and relevant coroutine signatures;
- delivery/reconnect/error counts;
- cleanup counts for containers, networks, and volumes.

## Build the candidate without changing dependencies

1. Transfer the exact reviewed revision with `git archive <revision>`, not an uncommitted workspace copy.
2. Verify large replay fixtures after transfer with SHA-256.
3. Build a source overlay:

```dockerfile
FROM registry.example.com/app:<baseline-tag>
WORKDIR /app
COPY src /app/src
```

Tag it locally and set `pull_policy: never` in the Compose override. The only intended variable is source code; dependencies, OS layer, architecture, and entrypoint remain those of the baseline release image.

**Limitation:** this proves runtime behavior against the baseline image environment. It does not replace a fresh production-image build or dependency-resolution check. State that explicitly.

## Compose isolation

- Use a different Compose project name for every baseline and candidate run.
- Prefer project-scoped named volumes in the override, even if the base Compose file uses bind-mounted DB data. Compose volume entries are merged by container target, so overriding the same target isolates each run.
- Put replay/load generation in a Compose service attached to the same application network; avoid ad-hoc `docker run` containers.
- Use identical ports, flags, capture, subscriber topology, request rate, and duration across sequential A/B runs.
- Record the exact baseline image ID/tag and candidate revision.

## Subscriber pressure pattern

For a realtime subscription regression, combine:

- N stable subscribers to reproduce fanout cost;
- one short-lived subscriber that repeatedly connects, starts a subscription, waits briefly, then disconnects to exercise cancellation cleanup;
- concurrent polling of the latency-sensitive REST endpoint at a fixed rate.

Record both the stable count and peak active count: N stable plus one churn client briefly produces N+1 active subscriptions. Match whichever production quantity matters instead of calling N stable subscribers “production-equivalent” without qualification.

Do not count a WebSocket handshake as sufficient. Verify subscriptions receive `next` messages and report per-subscriber message counts. For churn, report successful sessions and errors. For `LATEST`/coalescing subscriptions, received-message count is a throughput/freshness indicator, not an every-input completeness assertion.

## Capture preflight

Before a timed replay, inspect the fixture rather than assuming chronological order:

- count rows by topic/payload class;
- record first/last timestamps and whether timestamps are ascending, descending, or mixed;
- compute the intended source span and expected wall duration at the requested replay speed;
- verify the transferred fixture by checksum.

Some retained captures are reverse chronological. If replaying in file order, using absolute inter-row deltas can preserve cadence, but record the direction and report a positive elapsed span. Alternatively sort explicitly before both A/B runs. Never allow a negative `capture_span_seconds` field to enter the final report without correcting or explaining it, and never silently change ordering between baseline and candidate.

## Secret handling on remote playgrounds

When the base Compose file already contains an API key or other credential:

- extract it at runtime into an environment variable without printing it;
- pass it only to the load service environment;
- do not copy it into scripts, artifacts, chat output, or the task plan;
- ensure command tracing (`set -x`) is disabled around extraction and invocation.

## Runner structure

Use one orchestration script with a cleanup trap:

1. Build/load the candidate and load-tool images.
2. Start broker and database with `docker compose up -d --wait`.
3. Run migration through Compose.
4. Start the application and wait for its health check.
5. Start per-second container stats collection.
6. Run the Compose load-tool service.
7. Stop stats collection; capture application logs and `compose ps` before teardown.
8. Summarize endpoint latency and pending-task warning counts.
9. Run `docker compose down -v --remove-orphans` in the trap.
10. Assert zero remaining containers, networks, and volumes for that project label.

A long bounded remote run may be started as a tracked background terminal process with completion notification. Never launch an untracked SSH/nohup job.

## Interpretation

- A source-overlay candidate outperforming the stock release under identical load is strong causal validation for the code change.
- Zero endpoint requests above the caller deadline and zero pending-task warnings are acceptance evidence for that lab workload only.
- A playground run is not automatically production proof. Report architecture, replay speed, payload mix, DB contents, subscriber topology, and any missing production traffic.
- Empty or lightly seeded DB results isolate event-loop responsiveness but may not represent production query time; preserve that distinction in the conclusion.
