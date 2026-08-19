# Route-authorized but facing-signal-red stall

Use this reference when a vehicle reaches a current block, WSS repeatedly reports the route as authorized, but the vehicle does not enter the next block and the route later times out.

## Diagnostic distinction

Do not assume that a later `AUTHORIZED → TIMEOUT` caused the stop. Establish ordering:

```text
conflicting route/block clears
→ route and controlled blocks become AUTHORIZED
→ MA range refreshes
→ expected facing signal remains RED
→ no block exit
→ fixed-duration route TIMEOUT
→ clear/re-request restores the same authority
```

A timeout at an exact repeated interval after authorization is often the consequence of an unused route. Measure `first usable authorization → first timeout`; if Thalos restores authorization within seconds but movement still does not resume, classify timeout/retry as amplification rather than the first divergence.

## Required joins

1. ADS-reported current block and block exit.
2. WSS occupancy and authorization for every route-controlled block.
3. Route state and owner.
4. Facing-signal aspect before and after route authorization.
5. MA range refresh and, when available, raw Type 3 payload plus Type 4 ACK.
6. MQTT status cadence to distinguish no movement from telemetry loss.
7. A normal movement on the same path close in time.

A route and its blocks can be authorized while the associated signal remains RED. Treat that as an interlocking/WSS/OpenPLC inconsistency candidate, not as valid movement authority merely because the route state is `AUTHORIZED`.

## Same-path comparator

For a normal comparator, align:

```text
route authorization confirmed
→ current-nibble authority validation
→ MA refresh
→ facing signal RED → permissive
→ current-block exit
```

Then compare the failed trip. The strongest divergence is not route-request churn shared by both trips, but the first event missing only from the failed trip—for example, no permissive signal and no current-block exit after usable authority.

## Raw WSS-agent query strategy

WSS-agent DEBUG output can exceed Loki limits in seconds because every Modbus snapshot dumps all nodes. Never query it broadly. Use short windows and exact server-side filters such as:

```logql
{job="containers", service_name="alpha-wss-agent-1"}
|~ "name: +1-3WD|name: +11, status"
```

Separate read-side node addresses (actual interlocking state) from write-side addresses (requested setting). Do not merge alternating read/write values into one state sequence. Reduce each side independently to state changes.

Use higher-level Thalos `wss_agent_service` logs for the causal timeline, then raw WSS-agent state dumps only to confirm what the interlocking reported.

## MA proof boundary

Current Thalos behavior refreshes `facing_sig_stat` and `next_facing_sig_stat` from the WSS cache before each MA dispatch. This supports a high-confidence inference that a persistent RED WSS signal is propagated into refreshed MAs. It is not raw payload proof.

To close the proof boundary, capture:

- Type 3 MA payload after the route became usable;
- matching MAID Type 4 ACK/rejection;
- OpenPLC/interlocking diagnostics in the same sub-second window;
- ADS controller/traction decision logs if the physical stop mechanism matters.

MQTT-recorder topic cadence proves only that status messages continued; it does not prove MA acceptance, signal field values, operating mode, or traction state.

## Additional anomaly to record

Compare ADS-reported current block with WSS occupancy. If ADS remains in a block while WSS reports it FREE or allows other traffic through that block, record a cross-layer occupancy mismatch. It may be a separate wayside detection defect or part of the signal failure, but do not merge it into the root cause without interlocking evidence.
