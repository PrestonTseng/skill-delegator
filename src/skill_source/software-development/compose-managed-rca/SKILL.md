---
name: compose-managed-rca
description: "Run multi-container RCA/performance investigations with Docker Compose, per-stage timing, one-variable isolation, and guaranteed cleanup."
version: 1.0.0
author: Tapas Manager
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [docker-compose, rca, performance, debugging, multi-container]
    related_skills: [systematic-debugging, webapp-testing, indexed-codebase-inspection]
---

# Compose-Managed RCA

Use this skill when investigating a bug/performance issue that requires starting multiple Docker containers: app, API, broker, DB, frontend, browser collector, workers, or test tools.

## Core Rule

When a task needs multiple Docker containers, use Docker Compose. Do not leave ad-hoc `docker run` containers behind.

Every experiment must:

1. Use a distinct Compose project/run name.
2. Start the whole stack with `docker compose up` / `docker compose run`.
3. Write artifacts to a run-specific output directory.
4. Collect logs before teardown.
5. Run `docker compose down -v --remove-orphans` in a `finally`/trap path.
6. Verify no containers remain for that Compose project before claiming completion.

## Workflow

### 1. Define the evidence question

State the one thing this run should prove or falsify, for example:

- Does delay occur before the service receives messages?
- Does disabling one subscriber remove broker pressure?
- Does frontend render remain fast when delivery is slow?

Avoid broad “run everything and see” tests. Each run should have one variable changed.

### 2. Build a Compose stack

Prefer explicit services:

- broker / queue
- database
- API/service under test
- frontend if relevant
- tools/replay container
- browser/collector container

Expose only needed ports. Use service DNS names in container-to-container config.

When an existing config expects a legacy hostname, add a Compose network alias rather than patching production config just for the test.

### 3. Parameterize runs

Support these through environment variables or script params:

- `COMPOSE_PROJECT_NAME`
- output directory
- route/page set
- replay speed / limit / start offset
- image tags
- feature flags / subscriber toggles
- test duration

This makes A/B testing repeatable and prevents hardcoded one-off experiments.

### 4. Instrument component boundaries

For each boundary, log timestamps and trace IDs:

- source publish / capture time
- broker/client receive
- handler start/end
- pubsub publish/done
- websocket/subscription receive
- browser processing/render observed

Use a stable trace key where no single unique id exists. For packet-level RCA, prefer an explicit packet/correlation id propagated through the payload or message metadata. If you must join by a repeated trace key, treat the result as provisional and use order-based joining only to validate the instrumentation path.

For UI stalls, collect raw WebSocket message cadence separately from app subscription/component/render timing. If WebSocket gaps and subscription gaps line up, the stall is upstream of component/render code.

For realtime subscription stalls, explicitly test whether the pubsub layer coalesces updates. A latest-value store plus binary event/wakeup can drop intermediate snapshots without looking like an error. Use a one-variable queue-mode diagnostic to distinguish intentional/latest-value semantics from unintended delivery loss; see `references/packet-level-websocket-stall-tracing.md`.

### 5. Run one-variable isolation

Change exactly one variable between A/B runs:

- one subscriber enabled vs disabled
- one route vs multiple routes
- replay speed 2x vs 5x
- old image vs new image
- config flag on vs off

Do not compare runs that differ in architecture, image variant, replay file, route count, and feature flags all at once.

### 6. Analyze before concluding

For each run, report:

- input count
- received count at each stage
- drop/error/reconnect count
- p50/p95/p99/max per stage
- >200ms/>500ms/>1s/>2s counts where useful
- whether cleanup was verified

Separate synthetic overload signatures from production RCA. A lab stress failure shows how the system fails under load; it is not automatically the production root cause unless production evidence matches.

## Pitfalls

- **Ad-hoc containers hide state.** If a failed run leaves old containers/networks, the next run may be invalid.
- **High replay rates can create artificial failures.** First find a stable envelope, then push toward threshold.
- **Architecture mismatch matters.** Avoid using an amd64 image under emulation on an arm64 host for performance claims.
- **Windows Docker Desktop over SSH can fail before app code runs.** If build/pull fails with Docker Desktop credential-helper errors like `A specified logon session does not exist`, separate infrastructure failure from app validation. For Windows AMD64 hosts, build `linux/amd64` images where network/source access works, transfer with `docker save`/`docker load`, and run a temporary Compose override with `pull_policy: never`. Retain the base Compose topology and use the requested application image tags through a run-specific env file; see `references/windows-docker-desktop-ssh.md` and `references/windows-full-compose-validation.md`.
- **Logs are not proof of absence.** If production lacks a lab drop signature, demote that hypothesis and add per-stage timing.
- **One disabled component can isolate an overload amplifier.** If disabling one subscriber turns the same replay from failing to stable, prioritize that component for production checks.
- **Separate app-flow coupling from shared-source coupling.** A side consumer may not be in the failing UI/API path, but can still affect it through a shared broker topic, queue, DB table, or network resource. Verify both the application data flow and the shared infrastructure flow before naming a cause.
- **Inspect installed dependency source when behavior lives in a wheel/package.** If code imports a package whose source is installed during build, download/extract the exact wheel or inspect it inside the built image. Do not infer package behavior from the wrapper code alone.
- **Do not confuse a source-overlay image with a fresh production build.** A candidate built `FROM` the exact baseline release image and `COPY`ing only reviewed source is useful one-variable runtime evidence when dependency resolution is unavailable, but it does not verify dependency installation or the production Dockerfile. Record the limitation and follow `references/source-overlay-ab-validation.md`.

## Verification Checklist

Before final response:

- [ ] Compose project name recorded.
- [ ] Logs/artifacts copied to durable run directory.
- [ ] `docker compose down -v --remove-orphans` executed.
- [ ] No containers remain for that Compose project.
- [ ] One-variable difference between compared runs is clear.
- [ ] Production-equivalence limits are stated.

## References

- `references/windows-docker-desktop-ssh.md` — runbook for remote Windows Docker Desktop validation over SSH when credential helpers or private registry pulls block normal compose build/pull; includes amd64 `docker save`/`docker load` workaround.
- `references/windows-full-compose-validation.md` — full-stack validation recipe: exact image-tag env file, local-image Compose override, dependency-order startup/migration, interaction-level assertions, and schema compatibility regression loop.
- `references/sart1929-vehicle-status-hub.md` — case study: SART-1929 MQTT/Crystal RCA; Compose-managed stack isolated `VehicleStatusHubSubscriber` as a lab overload amplifier while preserving the distinction from Alpha production evidence.
- `references/packet-level-websocket-stall-tracing.md` — pattern notes for packet-level publisher→browser timing, raw WebSocket cadence capture, and separating subscription delivery stalls from UI render stalls.
- `references/source-overlay-ab-validation.md` — one-variable remote A/B recipe using an exact release image plus reviewed source overlay, retained MQTT replay, stable/churn subscribers, concurrent endpoint polling, secret-safe runtime extraction, and strict Compose cleanup.
