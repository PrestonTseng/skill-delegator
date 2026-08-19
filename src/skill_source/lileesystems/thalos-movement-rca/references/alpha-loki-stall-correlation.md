# Alpha Loki multi-layer stall correlation

Use this reference when a vehicle reaches a block but never advances, especially when route authorization initially fails and later recovers.

## Proven query method

Query Alpha Loki with `/loki/api/v1/query_range`, `direction=forward`, and server-side LogQL filters. Split broad windows into bounded chunks (for example, two hours for vehicle-filtered queries and 30–60 seconds for unfiltered Thalos queries), deduplicate `(timestamp, line)`, and treat any chunk that reaches `limit` as incomplete.

Cover both UTC and site-local date boundaries before narrowing the incident window. For an Asia/Taipei incident date, include the corresponding previous-day `16:00Z` boundary.

Start with:

```logql
{job="containers", service_name="thalos"} |= "<service-or-vehicle-id>"
```

Then correlate the narrow divergence window with:

```logql
{job="containers", service_name="thalos"} |~ "Updated WSS status route|Updated block|Updated signal|Updated authorized range|Requesting authorization|timeout|entered block|exited block"
```

Discover adjacent evidence sources through Loki label values rather than assuming Thalos is the only service. Alpha commonly includes `alpha-mqtt-recorder-mqtt-recorder-1`, `alpha-wss-agent-1`, and SafeART services.

## Causal decomposition

Do not treat the final repeated timeout as the root cause. Build these layers:

1. Last confirmed vehicle block transition.
2. First route request and why it was denied.
3. Earlier mission/route that still held overlapping controlled blocks.
4. Exact moment the route, controlled blocks, and facing signal became valid.
5. Movement-authority range sent after recovery.
6. Whether the vehicle then exited the current block.
7. Whether status telemetry remained live.
8. Mission completion, termination, or indefinite wait.

Compute and report separate durations for the initial interlocking/gating delay, the valid-authority-to-no-movement interval, and the total stall. This prevents a short upstream route conflict from being mislabeled as the cause of a much longer downstream non-movement.

## Strong comparison

Find a normal movement on the same mission/path close in time. Compare the interval from valid route/MA to block exit. A same-path comparator is stronger than a generic expected timeout and helps establish that the observed wait is abnormal.

## Telemetry proof boundary

MQTT-recorder topic lines can establish that status messages continued to arrive (for example, `/v1/obs/status/<ads-id>` at a steady cadence). They do **not** reveal payload content, MA acceptance, operating mode, brake state, traction inhibit, or controller decisions unless payload bodies are separately captured.

Therefore:

- continued status topics rule out a simple telemetry disconnect;
- they do not prove that ADS accepted or acted on an MA;
- if route, blocks, signal, and MA are valid but the vehicle never changes block, place the direct observable failure downstream of Thalos authority generation;
- name the exact internal ADS/vehicle cause as unproven until ADS/controller diagnostics or raw MQTT payloads are available.

## Session-derived example pattern

In the 2026-08-16 Alpha 284U case, an earlier Route 2 explained only the first ~7-minute Route 6 delay. After Route 6, C2T/H2T authority, signal 2R, and MA became valid, the ADS continued publishing status but never left E1T for over 12 hours. The correct conclusion separated the initial route conflict from the long vehicle-side non-movement and preserved the ADS-internal proof boundary.
