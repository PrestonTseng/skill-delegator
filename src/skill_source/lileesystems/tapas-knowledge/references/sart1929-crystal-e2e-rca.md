# SART-1929 Crystal end-to-end RCA pattern

Use this reference for TAPAS / SafeART realtime track-map latency investigations that must include the real Crystal frontend, not only a headless GraphQL subscriber.

## When to use

Use when the suspected path is:

```text
MQTT publish -> Unicorn MQTT subscriber -> Unicorn pubsub/GraphQL subscription -> Crystal receive -> Crystal render/paint
```

Especially use it when backend-only replay is clean but users still report delayed or bursty Crystal track-map updates.

## Key lessons

- Build architecture-specific images for the execution host. If the remote Windows host is amd64 and the local host is arm64, build Docker images with `--platform linux/amd64` and transfer/load those images remotely.
- Backend-only replay can miss the real failure mode. Re-run with actual Crystal pages open, ideally M1/M2/M3 simultaneously when that matches the symptom.
- Measure every boundary with a trace key or RCA-only trace fields. Suggested fields:
  - MQTT replay publish timestamp.
  - Unicorn MQTT received timestamp.
  - Unicorn handler/convert/pubsub timestamps.
  - Crystal subscription receive timestamp.
  - Crystal component-processed timestamp.
  - Crystal render/paint-observed timestamp.
- For Crystal, capture both `Date.now()` and `performance.now()`: epoch time helps cross-process joins; performance time helps browser-only deltas.
- Use browser `PerformanceObserver` long-task events to distinguish frontend main-thread stalls from backend/broker delay.
- Full-snapshot subscription semantics mean repeated vehicle rows are not automatically duplicate source data or backend backlog. Distinguish snapshot members from the update that triggered the snapshot.

## Real-Crystal instrumentation seams

Crystal 0.21b2 seams used successfully:

- Websocket client setup: `apps/crystal/src/app/core/graphql/graphql.provider.ts`.
- Vehicle subscription receive: `TrackMapService.subscribeToVehicleStatus()`.
- M1/M2/M3 processing: `M1Component.ngOnInit()`, `M2Component.ngOnInit()`, `M3Component.ngOnInit()`.
- Render boundary: `TrackMapComponent.ngOnChanges()` plus a double `requestAnimationFrame` callback for post-render observation.
- Long tasks: `PerformanceObserver({ type: 'longtask', buffered: true })`.

## Presentation charts to generate

At minimum generate:

1. Absolute per-record pipeline timeline: publish, Unicorn received, Unicorn pubsub done, Crystal received, render observed.
2. Stage-latency scatter over event sequence with threshold lines at 200ms, 500ms, 1s, and 2s.
3. Rolling p50/p95/p99 by stage to show stable vs increasing latency.
4. End-to-end latency histogram/CDF.
5. Stall/burst detector: inter-arrival gaps and number of records delivered after each gap.
6. Browser long-task duration overlay.
7. Per-route or per-vehicle breakdown when M1/M2/M3 are open together.

## Evidence interpretation pattern

- Mosquitto logs such as `Outgoing messages are being dropped for client ...` are strong evidence of broker/client backpressure.
- If Mosquitto drops occur and Unicorn receives far fewer rows than the replay published, prioritize MQTT broker / Unicorn MQTT client backpressure over frontend render hypotheses.
- If Unicorn handler/lock/pubsub timing is sub-millisecond but `publish -> Unicorn received` is large, the slow section is before or at the MQTT client receive boundary.
- If `pubsub -> Crystal subscription` is large while Crystal receive->render is small, Crystal is observing delayed delivery but not necessarily causing the multi-second delay.
- If Crystal receive->render or browser long tasks exceed thresholds, compare 0.21b2 with the later frontend performance commit, but do not treat frontend optimization as the primary fix unless upstream timing is clean.
- A backend-only replay that is clean is not enough evidence to clear the full system. In SART-1929, adding real Crystal M1/M2/M3 pages changed the system behavior enough to reproduce Mosquitto outgoing-drop signatures on both the slow Windows host and the local native host.
- When both a slow host and local host reproduce broker drop under real Crystal, treat host speed as a magnitude/tail-shape factor, not the sole root cause. The more durable boundary is real frontend subscriptions / GraphQL fan-out / MQTT client pressure.
- Use local-vs-remote comparison runs to separate three questions: (1) does the failure class reproduce at all, (2) how much worse is the slow host, and (3) which stage changes shape. Compare receive ratio, Unicorn handler p95, pubsub→Crystal p95, Crystal receive→render p95, and long-task tail.

## Charting preference for presentation

For this class of RCA, prefer line charts over only scatter/CDF when the user wants to see whether latency is stable, spiky, or continuously rising:

- Publish → Unicorn MQTT received over processed vehicle sequence, with rolling mean and threshold lines at 200ms / 500ms / 1s / 2s.
- Unicorn handler total over sequence; this should remain near zero if the backend handler is not the bottleneck.
- Unicorn pubsub → Crystal subscription over Crystal event sequence.
- Crystal receive → render over render-observed event sequence.
- Browser long-task duration over event sequence.
- A p95 comparison bar chart is useful as the executive summary, but the line charts are the primary diagnostic view.

## Remote-run pitfalls and fixes

- Remote Windows Docker may not be able to pull images due credential-helper/login-session issues. Pull/build locally for linux/amd64, `docker save | gzip`, transfer, and `docker load` remotely.
- If using nginx to serve Crystal static files and proxy `/graphql`, ensure Unicorn is already resolvable on the Docker network before starting nginx; otherwise nginx may fail startup with `host not found in upstream`.
- For Unicorn test DBs, run Alembic migrations and seed default users before Playwright login.
- Use `python -m alembic ...` if the `alembic` console script is not on PATH inside the image.
