# Realtime Trackmap Delay RCA Pattern

Use this reference when investigating TAPAS realtime display delays where data flows through MQTT and a backend subscription layer, especially pipelines like:

```text
ADS / WSS → MQTT broker → Unicorn or another backend aggregator → GraphQL subscription/WebSocket → Crystal or another frontend
```

## Key lesson

If the suspected failure could involve MQTT broker/client behavior, replay captured messages through a **real local MQTT broker** instead of only calling backend handlers directly. Broker-mediated replay preserves topic filters, wildcard subscription behavior, MQTT client callback scheduling, broker buffering, reconnect behavior, packet pacing, and backpressure.

Direct handler replay is still valuable later as a differential test, but it should not replace broker-mediated replay when the RCA question includes broker/client buffering or delivery bursts.

## Recommended RCA layers

1. **Raw capture analyzer**
   - Stream large captures; do not load entire CSVs into memory.
   - Confirm capture ordering. Some captures may be newest-first; interval calculations must account for that.
   - Measure per-topic cadence and per-vehicle effective position-change cadence.
   - Distinguish raw repeated/stale vehicle position from downstream repeated/stale output.

2. **Broker-mediated replay**
   - Start a local broker such as Mosquitto.
   - Configure the backend under test to subscribe to the broker using production-like topic filters.
   - Publish captured rows into the broker at original cadence and optionally accelerated cadence.
   - Replay only relevant topic families first, e.g. `/v1/obs/status/+` and `/v1/wss/status/+` for trackmap RCA.

3. **Headless GraphQL/WebSocket subscriber**
   - Subscribe directly to the backend without Crystal/frontend rendering.
   - Log receive timestamp, payload timestamp if available, vehicle ID, effective position/state, payload size, and inter-arrival intervals.
   - This isolates backend delivery from browser/frontend behavior.

4. **Differential probes**
   - Compare raw MQTT capture cadence vs backend MQTT receive cadence vs backend publish cadence vs GraphQL client receive cadence.
   - Use direct handler replay only after broker-mediated replay to isolate transform cost from MQTT client/broker behavior.

## Evidence matrix

- Raw capture already has gaps/stale positions → upstream publisher or capture path likely.
- Raw capture stable, backend MQTT receive bursts → MQTT broker/client/subscriber behavior likely.
- Backend receive stable, backend publish bursts → backend aggregation, locking, event loop, or pubsub layer likely.
- Backend publish stable, GraphQL client receive bursts → GraphQL/WebSocket send or backpressure likely.
- Headless GraphQL stable, frontend DevTools burst → frontend/browser/network/rendering path likely.
- Backend and headless GraphQL stable, but real Crystal shows delay → instrument Crystal subscription, route-level processing, track-map `ngOnChanges`, and post-paint render observation; see `references/crystal-trackmap-e2e-rca.md`.

## Crystal/frontend extension

When Crystal itself is under suspicion, do not stop at the headless subscription client. Run the real Crystal version under test, preferably from an isolated release-tag worktree, and collect browser telemetry through Playwright. Join these frontend events with replay and Unicorn timestamps:

```text
publish -> Unicorn MQTT received -> Unicorn pubsub/GraphQL publish -> Crystal subscription received -> M1/M2/M3 processed -> TrackMap render observed
```

For presentation, generate pipeline scatter timelines, stage-latency-over-time charts, rolling p95/p99, publish-to-render histograms/CDFs, stall/burst charts with 200ms+ thresholds, per-vehicle heatmaps, and browser long-task overlays.

Use native Docker images on the target host for primary evidence. Cross-architecture emulation can create false slow-subscriber/broker-overload signatures and should only be treated as a stress signal.

## Unicorn-specific inspection cues

When Unicorn is the backend aggregator, inspect:

- MQTT subscriber jobs and configured topic filters.
- `RealtimeVehicleHandler.update_realtime_vehicle()` behavior: whether all vehicles share one lock, whether each update publishes the full last-known vehicle dictionary, and whether unchanged positions are re-emitted.
- Wayside status aggregation/publish path.
- PubSub implementation semantics: latest-only event/data vs queued all-events delivery.
- GraphQL subscription resolver: whether it yields full snapshots, filtered vehicle lists, or per-event deltas.

## Temporary instrumentation guidance

- Use a unique prefix such as `[SART1929-RCA]` or `[RCA-<ticket>]` so cleanup is safe.
- Measure handler start/end latency, transform latency, publish latency, event-loop lag, queue/pending counts where available, and GraphQL receive intervals.
- For real frontend runs, also instrument Crystal subscription receive, M1/M2/M3 component processing, TrackMap `ngOnChanges`, double-`requestAnimationFrame` render observation, and browser long tasks.
- Generate presentation-ready charts: absolute per-record pipeline timelines, stage-latency scatter/trends, rolling percentiles, end-to-end CDF, stall/burst detector, and long-task overlay.
- If the remote test host architecture differs from the local host, build/load Docker images for the remote architecture explicitly, e.g. `--platform linux/amd64` for an amd64 Windows Docker host.
- Do not turn an RCA instrumentation patch into a product fix without a separate approved plan.

See also `references/sart1929-crystal-e2e-rca.md` for the real-Crystal end-to-end measurement pattern.
