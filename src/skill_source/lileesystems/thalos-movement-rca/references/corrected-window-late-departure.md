# Corrected-window late-departure analysis

Use this reference when reconstructing Thalos departure timing from filtered Loki JSONL exports. The July 2026 Alpha example established a reusable segmentation and several proof boundaries.

## Count at two levels

Report both, because “departure attempt” is ambiguous:

1. **Mission attempts:** count `ROUTE_AUTHORIZED --(depart)--> DEPARTING`, then classify by `depart_ok` versus `depart_fail`.
2. **MA authorization attempts:** count `Authorize vehicle departure attempt … failed` plus successful `Departure command issued` events.

A Mission can enter `DEPARTING` but never call `authorize_depart`: the departure Nibble must first reach `AWAIT_BLOCK_EXIT`. In the corrected window, every pre-command failure was an `AWAIT_BLOCK_ENTRY_TIMEOUT_ERROR`, so counting only MA commands would hide those Mission attempts.

## Timeline segmentation

For each Mission/service ID, join nanosecond timestamps into:

```text
AWAIT_DEPARTURE entered
-> door_close
-> DEPARTING
-> Departure command issued
-> DEPARTED or DEPART_ERROR
```

Interpret the segments as follows:

| Segment | Meaning and caveat |
|---|---|
| `AWAIT_DEPARTURE -> door_close` | Scheduled timer hold. Check `_calculate_depart_delay_ms`; do not call this operational lateness without comparing to the planned depart time. |
| `door_close -> DEPARTING` | Door/mission-route gate. If door handling is placeholder/immediate in the running generation, this is principally route authorization/FSM gating. Without detailed WSS lines, label it a bounded route/FSM window rather than a proven WSS denial. |
| `DEPARTING -> command` | Departure-Nibble readiness + route/MA refresh + signal gate + MA dispatch/ACK wait. Split only when detailed Nibble, signal-retry, or ACK evidence exists. |
| `command -> DEPARTED` | Usually physical first-block exit and departure-Nibble completion, not ACK time. |
| `DEPARTING -> DEPART_ERROR` with no command | Pre-command readiness failure, commonly first-block entry timeout. |

Use the exact Loki `ns` field for calculations; the rendered millisecond timestamp is presentation only.

## Signal-delay proof pattern

A defensible signal-delay finding requires this ordering:

```text
fresh facing-signal calculation/update
-> authorize_depart attempt rejects current aspect
-> configured retry interval
-> another rejection or eventual command
```

This proves a live aspect gate. It does **not** prove a stale facing-signal ID when the ID was freshly calculated and written immediately before the checks. Note that the error text may say “not GREEN” while source accepts GREEN and directional proceed aspects such as FORWARD/FORWARD_LEFT/FORWARD_RIGHT.

## ADS ACK proof boundary

Read the running implementation before interpreting `Departure command issued`:

- `send_command` may await the ADS ACK before returning;
- `_dispatch_command` may log a warning and swallow a false/timeout result;
- `authorize_depart` may still emit `Departure command issued` afterward.

Therefore the command log alone is not positive ACK proof. Match the exact departure-command MAID against timeout/rejection/ACK logs. If positive ACKs are below the deployed log level, state that no ACK failure was observed rather than claiming a proven successful ACK. Do not assign `command -> DEPARTED` to ACK latency.

## Missing/truncated evidence

Filtered exports often omit global WSS state or hit a Loki result cap. Record each file’s first/last timestamp and line count before analysis. If the broad export ends before an anomaly, use outer FSM bounds and explicitly avoid inventing route retries or signal transitions. A missing expected artifact should be reported as a proof limitation, not silently substituted.

## Useful output shape

Keep the parent-facing result compact:

- revision and corrected UTC window;
- Mission attempts / successes / failures;
- MA authorization attempts / accepted commands / signal rejections;
- schedule-hold distribution;
- only nontrivial route and pre-command windows;
- all failures with exact terminal reason;
- signal and ADS proof boundaries;
- confirmation that no files were changed.
