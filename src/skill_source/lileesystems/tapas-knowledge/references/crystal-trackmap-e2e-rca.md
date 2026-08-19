# Crystal track-map end-to-end RCA pattern

Use this reference when realtime track-map delay may involve Crystal/frontend rendering, not only MQTT → Unicorn → GraphQL delivery. This extends the backend replay pattern to the full path:

```text
MQTT replay publish -> Unicorn MQTT received -> Unicorn GraphQL/pubsub publish -> Crystal subscription received -> M1/M2/M3 processing -> TrackMap render observed
```

## When to use

- Backend/headless GraphQL subscriber timing is clean, but user-visible Crystal track-map still appears delayed or bursty.
- A frontend performance commit may affect the symptom and must be compared against a release tag.
- The user asks for per-record, presentation-ready timing charts across backend and frontend boundaries.

## Repository setup

- Index both the current Crystal repo and the exact release worktree with Codebase Memory before broad grep.
- Use an isolated worktree for the release under test; do not disturb the user's main checkout.
- For SART-1929-style work, first test `safeart-0.21b2`, then compare later frontend performance commits only after the baseline is measured.

## Crystal seams to inspect / instrument

Typical Crystal track-map path:

- GraphQL websocket client: `apps/crystal/src/app/core/graphql/graphql.provider.ts` (`GraphQLWsLink(createClient(...))`).
- Subscription service: `TrackMapService.subscribeToVehicleStatus()`.
- M1/M2/M3 route processing: `M1Component.ngOnInit()`, `M2Component.ngOnInit()`, `M3Component.ngOnInit()`.
- Render seam: `TrackMapComponent.ngOnChanges()` plus `track-map.component.html` vehicle DOM rendering.

Post-baseline performance commits may change these seams directly, especially change detection strategy, DOM clamp/directive logic, signal drawing, or vehicle list processing.

## Trace identity

Prefer a durable temporary RCA trace id carried from replay payload through Unicorn GraphQL to Crystal. If the backend model does not preserve unknown fields, fall back to a trace key and ordered occurrence matching:

```text
vehicle_id|milepost|block_id|sub_block_id|lane_id
```

Mark ambiguous joins explicitly because Unicorn/Crystal subscription snapshots can re-emit unchanged vehicles and coalesce intermediate updates.

## Frontend telemetry events

Record JSON-compatible events in `window.__SART1929_RCA_EVENTS__` and console log them with a unique prefix such as `[SART1929-RCA]`:

- `crystal_subscription_received`: in `TrackMapService.subscribeToVehicleStatus()` before mapping/processing.
- `crystal_m_component_processed`: after M1/M2/M3 filtering/mapping and before assigning the input list.
- `crystal_trackmap_ng_on_changes_start` / `crystal_trackmap_ng_on_changes_end`: inside `TrackMapComponent.ngOnChanges()`.
- `crystal_render_observed`: after render/paint observation, e.g. double `requestAnimationFrame` after the input change.
- `browser_longtask`: optional `PerformanceObserver` long-task entries to correlate main-thread stalls.

Each event should include:

- trace id/key and vehicle fields (`adsId`, `milepost`, `blockId`, `subBlockId`, `laneId`),
- backend timestamps propagated in GraphQL payload,
- `Date.now()` for cross-process epoch joins,
- `performance.now()` for browser-only deltas,
- route (`M1`, `M2`, `M3`), snapshot size, and rendered vehicle count.

## Remote real-Crystal test pattern

1. Start backend replay environment on the target host with production-equivalent architecture images; avoid cross-architecture emulation for primary evidence.
2. Start Crystal from the exact release worktree and point it at the test Unicorn GraphQL endpoint.
3. Use Playwright/Chromium to open the real M1/M2/M3 page(s).
4. Start MQTT replay.
5. Capture browser console RCA events and periodically dump `window.__SART1929_RCA_EVENTS__`.
6. Join replay, Unicorn, subscription, component, and render events into a canonical dataset.
7. If the release baseline shows frontend-side delay, repeat the same harness on the candidate performance commit and compare.

## Required charts for quick diagnosis

Generate charts suitable for Confluence/slides:

1. Pipeline scatter timeline: record sequence/replay time vs absolute timestamp offset for publish, Unicorn receive, pubsub/GraphQL publish, Crystal receive, and render observed.
2. Stage latency **line charts over event sequence** with 200ms / 500ms / 1s / 2s threshold lines. Prefer these when the user asks whether delay is stable, fluctuating, or continuously increasing.
3. Rolling p50/p95/p99 stage latency to distinguish sustained growth from jitter.
4. End-to-end publish-to-render histogram and CDF.
5. Stall/burst detector: inter-arrival/render gaps and number of records observed immediately after each gap.
6. Per-vehicle heatmap of frontend and end-to-end latency.
7. Browser long-task overlay when available.
8. Local-vs-remote comparison charts when a slow target host is involved: publish→backend receive, backend handler total, backend pubsub→Crystal subscription, Crystal receive→render, browser long tasks, and p95 summary bars.

## Interpretation pitfalls

- Full-snapshot subscription output can make unchanged vehicles look like duplicate source data. Do not call this backlog unless timestamps prove delayed delivery.
- Browser `performance.now()` is monotonic but process-local; use `Date.now()` / backend epoch timestamps for cross-node joins, and `performance.now()` for frontend deltas.
- A normal headless GraphQL subscriber being clean does not rule out Crystal main-thread, Angular change detection, DOM, image, layout stalls, or subscription fan-out pressure from real pages.
- Emulated Docker architecture can create false overload signatures; treat it as stress-only and rerun with native images before drawing conclusions.
- Audit broker image parity before making production claims. If Alpha uses `registry.lileesystems.com/eclipse-mosquitto:2.0.18-openssl`, do not silently substitute the public `eclipse-mosquitto:2.0.18` image for root-cause evidence; if the Alpha image is only available as AMD64, run it on an AMD64 host rather than under local ARM64 emulation.
- Treat replay speed as a first-class experimental variable. A `10x` replay can be a stress test rather than production-equivalent load; narrow to one page (for example `/m1`) and map thresholds such as `5x`, `7.5x`, and `10x` before declaring a bottleneck.
- If real Crystal pages reproduce Mosquitto `Outgoing messages are being dropped for client ...` while backend-only replay is clean, treat it as a broker/client backpressure stress signal, but do **not** claim the same root cause for Alpha when Alpha broker logs for the incident window do not contain that message. Use direct Alpha boundary timing instead.
- When both the slow target host and a local/native host reproduce the same broker-drop signature, host speed is a performance amplifier, not the sole root cause. Compare stage shapes and receive ratios rather than declaring the issue machine-specific.

## Session-specific threshold notes

See `references/sart1929-mqtt-replay-thresholds.md` for the SART-1929 image audit and threshold-test notes: local `/m1` at `5x` completed all `18,000 / 18,000` vehicle rows with no broker drop, while `/m1` at `10x` reproduced drops; the Alpha broker image was validated on Windows AMD64 and also dropped at `/m1` `10x`. Use that reference as a caution against over-interpreting synthetic `10x` failures.
