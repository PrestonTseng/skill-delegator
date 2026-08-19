# SART-1929 MQTT replay threshold and image-audit notes

Session-specific detail for future realtime track-map RCA runs. Use with `references/crystal-trackmap-e2e-rca.md`.

## Key correction from the user

Do not assume local real-Crystal stress failures mean the local host is inherently too slow. In this session:

- pure Crystal tests had been OK;
- pure Unicorn/backend replay had been OK;
- the failure appeared when combining real Crystal pages with aggressive MQTT replay;
- reducing to one page and lowering replay speed showed the local host could process the full dataset.

## Broker image parity

Alpha broker image:

```text
registry.lileesystems.com/eclipse-mosquitto:2.0.18-openssl
```

Lessons:

- Audit image architecture before using a run as performance evidence.
- The Alpha `openssl` broker image observed in this session was `amd64`.
- The local host was `arm64`; running the Alpha image locally would introduce emulation and is not primary evidence.
- Use a native AMD64 host for Alpha-broker image comparisons, or build/pull the matching native architecture.
- If a broker image differs from Alpha, say so explicitly and treat the result as a harness/stress signal, not production-equivalent evidence.

## Mosquitto drop log interpretation

`Outgoing messages are being dropped for client ...` means Mosquitto is dropping outbound messages for a slow/blocked subscribed client. It is a strong synthetic backpressure signal, but it is not proof that Alpha had the same issue.

If Alpha logs for the incident window do **not** show the message:

- do not present broker outgoing-drop as the Alpha root cause;
- keep it as a reproduction-environment stress signal only;
- verify whether Alpha log level/version/config would emit the line;
- rely on direct Alpha boundary timing to locate the real delay.

## Single-page threshold results from this session

Old capture:

```text
/opt/data/workspace/mqtt_raw_202607161910.csv
vehicle rows: 18,000
```

M1-only local ARM64, native official Mosquitto-derived image:

- `/m1`, `10x`: Unicorn received `4,523 / 18,000`; Mosquitto drop lines `6`.
- `/m1`, `5x`: Unicorn received `18,000 / 18,000`; Mosquitto drop lines `0`.
  - publish → Unicorn p95 about `469ms`, max about `927ms`;
  - Unicorn pubsub → Crystal subscription p95 about `151ms`, max about `921ms`;
  - Crystal receive → render p95 about `30ms`, max about `105ms`;
  - `ngOnChanges` p95 about `1ms`, max about `7ms`.

M1-only Windows AMD64 with Alpha broker image at `10x`:

- Unicorn received `3,968 / 18,000`;
- Mosquitto drop lines `7`;
- dropped client ids included Unicorn `vehicle_status_hub_subscriber_*` clients;
- Unicorn handler remained sub-millisecond p95.

Interpretation:

- `10x` is an aggressive stress condition and can overdrive even a one-page harness.
- `5x` one-page local run showed the local machine and Crystal render path were not inherently bottlenecked.
- Find the threshold before drawing root-cause conclusions.

## New capture noted for follow-up

```text
/opt/data/workspace/mqtt_raw_202607171123.csv
rows: 165,709
/v1/obs/status: 51,600
/v1/wss/status: 25,588
```

Recommended use:

1. First characterize thresholds on the older, smaller capture.
2. Then repeat only the most informative cases with the larger/newer capture.
3. Avoid using the larger capture as the first probe unless runtime is acceptable and the harness is already validated.

## Recommended threshold matrix

Start narrow:

```text
/m1 only: 5x, 7.5x, 10x
```

Then expand only if needed:

```text
/m1,/m2,/m3: 1x, 2x, 5x, 10x
```

Track for each cell:

- broker drop-line count;
- Unicorn MQTT received count vs vehicle publish count;
- Unicorn handler p95/max;
- pubsub → Crystal subscription p95/max;
- Crystal receive → render p95/max;
- browser long-task p95/max.

## Alpha RCA implication

For Alpha, direct timing instrumentation is still required:

```text
MQTT publish/capture
-> Unicorn MQTT received
-> Unicorn pubsub done
-> GraphQL/Crystal received
-> Crystal render observed
```

If Alpha has no broker drop logs, the synthetic drop failure mode should not be treated as the root cause. It only shows a possible stress boundary for the harness.
