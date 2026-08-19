---
name: thalos-movement-rca
description: Investigate SafeART/TAPAS Thalos late departure, movement stalls, Mission lifecycle/cancellation errors, ADS position, Nibble/Mission FSM, WSS block/route/signal state, and movement authority.
version: 1.7.2
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [lilee, safeart, tapas, thalos, rca, nibble, wss, ads, movement-authority]
---

# Thalos Movement RCA

## When to use

Use this skill for Thalos incidents where:

- a vehicle departs later than its scheduled time;
- a vehicle departs but stalls between blocks;
- Mission cancellation/termination produces API, JPS, cleanup, or late-event errors during movement testing;
- a Mission takes too long to complete after the terminal Nibble, or the next queued Mission appears to start late;
- reaches one segment but not the next;
- repeatedly rechecks, revokes, or requests a route;
- receives an allegedly stale/behind facing signal or invalid MA;
- times out in `AWAIT_BLOCK_ENTRY`, `AWAIT_BLOCK_EXIT`, or `ROUTE_REQUEST`;
- is suspected of racing ADS position against WSS block/route/signal changes.

Load `tapas-knowledge` alongside this skill for service/domain context. Use `systematic-debugging` for the general diagnosis loop.

## Required evidence order

1. **Read and normalize the exact incident source.** Fetch the user’s current Loki URLs, timestamps, vehicle IDs, and environment. Confirm whether supplied timestamps are UTC, local time, or browser-display time before interpreting URL parameters; record both the stated timezone and normalized UTC range using a time tool. If the user corrects a timezone/date/window, re-fetch and explicitly supersede every conclusion drawn from the prior window.
2. **Check query completeness.** Treat a result count equal to the Loki `limit` as truncated. Split the time range and/or use unsaturated server-side filters for departure, signal, route, terminate, API, exception, and lifecycle markers; preserve nanosecond timestamps for later joins.
3. **Identify the running code generation.** Match container IDs, startup/version logs, release tags/commits, and rollback timestamps before using local source as field evidence.
4. **Build vehicle timelines first.** Extract mission, Nibble, ADS block, departure, route request, recheck, and final error events.
5. **Join global WSS evidence from the same container/time window.** Vehicle filters often omit `wss_agent_service` route, block, signal, authorization, and retry events. When investigating why authorization disappeared, separate the observed state from provenance: correlate raw WSS block occupancy/authorization, TriOps Type 13 occupancy payloads, SS Type 8 route commands, and Thalos owner/request/revoke logs. Thalos Type 7 state has no actor or reason field, so preserve the audit boundary.
6. **Locate the first causal divergence.** Do not treat the final timeout as root cause when an earlier normal occupancy transition pushed the FSM into an abnormal state.
7. **Verify route topology and state semantics in source.** List controlled blocks, route owner, route state, listener lifecycle, and retry behavior.
8. **Reproduce the exact ordering with a deterministic probe or regression test.** Model old/new block overlap, ADS position update, old-block release, route reset, and WSS rejection.
9. **State proof boundaries.** Separate directly logged route/FSM failure from inferred physical stop mechanisms such as the exact facing-signal MA payload. For API reports, distinguish caller-visible HTTP failure from later internal cleanup errors.

## Timeline join

Normalize on Loki nanosecond timestamps and correlate:

```text
ADS position/block
-> WSS block occupancy + authorization
-> Nibble FSM transition
-> route state + owner
-> request/revoke result
-> MA/facing-signal update (when explicitly logged)
-> mission result
```

Useful counts:

- rechecks per Nibble/block and event source;
- route request/revoke attempts per Nibble;
- duration from first divergence to fault;
- delay between ADS entering the next block and the old Nibble completing.

## Late-departure timeline reconstruction

Count and report at two levels because “departure attempt” is ambiguous:

1. **Mission attempts:** `ROUTE_AUTHORIZED → DEPARTING`, classified by `DEPARTED` or `DEPART_ERROR`.
2. **MA authorization attempts:** failed `Authorize vehicle departure attempt` records plus `Departure command issued` records.

A Mission can enter `DEPARTING` and fail before `authorize_depart` because the departure Nibble has not reached `AWAIT_BLOCK_EXIT`. Identify pre-command Nibble failures separately.

Segment exact Loki `ns` timestamps as:

```text
AWAIT_DEPARTURE
-> door_close                 (scheduled timer hold)
-> DEPARTING                  (door/mission-route gate)
-> Departure command issued  (Nibble readiness + signal gate + dispatch/ACK wait)
-> DEPARTED / DEPART_ERROR    (first-block exit or failure)
```

Interpretation rules:

- Read `_calculate_depart_delay_ms` before calling the scheduled hold “late”; intentional offsets commonly explain it.
- Verify whether door handling is real or placeholder. If immediate, `door_close → DEPARTING` principally bounds route/FSM gating.
- Do not call the whole `DEPARTING → command` interval ADS delay; it also includes departure-Nibble route/MA readiness and signal checks.
- Do not call `command → DEPARTED` ACK latency; it usually measures physical first-block exit/Nibble completion.
- A command log is not necessarily positive ACK proof if dispatch swallows timeout/rejection. Match the exact MAID against ACK/error logs and state the proof boundary.
- If broad WSS evidence is truncated before the anomaly, report only outer bounds; do not invent retries or aspect transitions.

See `references/corrected-window-late-departure.md` for the compact analysis recipe and proof boundaries.

## Mission completion and next-Mission handoff

When an operator reports that a Mission takes too long to complete after the last Nibble, do not measure only terminal-Nibble completion to the next vehicle departure. Build a two-Mission handoff timeline:

```text
prior terminal Nibble COMPLETED
-> ARRIVING
-> ADS parked status
-> FINALIZING
-> ADS mission-end + JPS completion
-> prior COMPLETED
-> next Starting mission execution
-> ADS allocation/activation
-> scheduled departure hold
-> DEPARTING
```

Interpret each segment independently:

- The terminal Nibble completes when the vehicle enters the terminal block; Mission completion still requires ADS to report `ATO_PARKED_ON_PLATFORM` or `PARKED_OUT_PLATFORM`.
- `prior COMPLETED -> next start` measures coordinator queue handoff. A millisecond-scale gap falsifies a scheduler-delay hypothesis even when the next visible departure is much later.
- Split finalization into ADS mission-end notification and JPS completion; split the next Mission into ADS allocation, JPS activation, scheduled hold, and route/FSM gating.
- Read the departure-delay calculation before classifying `ACTIVATED -> door_close` as late. A 35–36 second interval can be the intentional schedule timer.
- Blank failures exactly at the configured HTTP timeout, followed by retry success, support external ADS/JPS latency but do not prove the exception type unless it is logged.

See `references/mission-handoff-latency.md` for the reusable timeline, interpretation rules, and a worked two-pair example.

## Stale-Nibble diagnostic pattern

Watch for:

```text
normal overlap makes next block OCCUPIED
-> current Nibble leaves AWAIT_BLOCK_EXIT for ROUTE_REQUEST
-> ADS enters next block while old Nibble does not complete
-> old block release/lost authorization triggers route revoke/re-request
-> requested route includes a block occupied by the train
-> WSS refuses authorization
-> retries amplify the stall
```

The decisive proof is the missed block-exit ordering, not merely the presence of `Rechecking route authorization...`.

## Mission cancellation crossover

When late-departure testing also reports Mission API terminate failures, trace cancellation as a multi-owner flow rather than treating every `ERROR` line as the API result:

```text
direct Thalos cancel API
-> coordinator cancel/terminate
-> MissionExecutor cleanup call to JPS
-> JPS mission state change
-> JPS service-removed event back to Thalos
-> possible second coordinator cancel
```

For each Mission UUID, join the direct API start and success/error marker, Mission FSM termination, JPS HTTP status/retries, cleanup/removal, and any later service-removed callback. A JPS `409`, timeout, `executor not found`, or `finalizing` error after a direct API success may be duplicate/late cleanup rather than caller-visible failure. Prove the client-visible HTTP status before describing it as an API failure.

Pair every direct API start with its terminal success/error marker and calculate endpoint latency. Report counts above plausible caller timeout thresholds (for example 10, 15, 20, and 30 seconds), not only min/median/max. A synchronous endpoint may eventually log success after its caller or UI has already timed out. This is a strong hypothesis for a reported API error, but it is not proof until the caller timeout and raw response are available.

Keep these outcomes distinct:

- explicit source-mapped 404/409/500;
- unresolved requests crossing the query boundary;
- server success after long best-effort cleanup;
- internal JPS retry/409/timeout logs swallowed by Mission termination.

Repeated lock/exec timer transition errors may be independent noise or amplification. Establish whether they precede and delay the specific cancellation/departure before treating their volume as causal.

### Mission-state auto-cancel propagation blind spot

When an external watchdog polls `thalos_mission_execution_state` and cancels Missions in an error category, do not assume a Nibble error has propagated to the Mission FSM. Thalos runs the current Nibble N and one look-ahead Nibble N+1 concurrently; a failed N+1 task can remain latent while the Mission coroutine is still awaiting blocked N.

Prove four layers separately:

1. **Nibble FSM:** did current or look-ahead Nibble enter `AWAIT_BLOCK_ENTRY_TIMEOUT_ERROR`, `ROUTE_REQUEST_ERROR`, or `MA_REFRESH_ERROR`?
2. **Task propagation:** did the failed Nibble task's exception reach `MissionExecutor._handle_nibble_executing`, or is the coroutine still awaiting a different current-Nibble task?
3. **Mission FSM/metric:** did Mission transition through `NIBBLE_EXECUTE_FAIL` to `NIBBLE_EXECUTE_ERROR`, and what value did `thalos_mission_execution_state` expose during the watchdog poll?
4. **Cancellation API:** did Thalos log `Cancelling mission with mission_uuid`, and did the endpoint reach a terminal success/error marker?

The decisive source pattern is:

```python
start task for current N
start task for look-ahead N+1
await task[N]  # N+1 may already have failed, but its exception is not observed
```

If N+1 fails while N remains pending, the surrounding `except` cannot emit `NIBBLE_EXECUTE_FAIL`; the Mission remains `NIBBLE_EXECUTING`, so a mission-state watchdog correctly skips it. If no Thalos cancel-start marker exists, classify the result as **watchdog did not call the endpoint**, not “cancel API failed.” Compare successful cancels in the same minute to rule out a global watchdog/endpoint outage, and treat later manual-mode cleanup as a separate owner and trigger.

See `references/lookahead-nibble-metrics-cancel-blind-spot.md` for the source path, deterministic reproduction, API attribution checks, repair contract, and missing inverse regression test.

### Publishing an auto-cancel RCA

When the user asks for a Confluence RCA, preserve the local RCA template but present the investigation in causal discovery order:

1. Show the vehicle, route, signal, and MA timeline. Separate an initial route delay from any later long stall.
2. Show the exact Nibble timeout transition and its 90-second duration.
3. State the watchdog contract precisely: n8n polls the **Mission state** metric and calls cancel only for an error-category Mission. Do not describe n8n as reading Nibble logs or Nibble metrics unless workflow evidence proves that behavior.
4. Prove whether the cancel API was called. Use the mission UUID, compare same-minute successful cancels, and keep later manual cleanup separate.
5. Show the complete Mission FSM timeline. The absence of `NIBBLE_EXECUTE_FAIL` after a logged Nibble error is a decisive state-propagation gap.
6. Trace the source path from the Nibble completion future to the Mission task supervisor. Then run the missing inverse case with current N pending and look-ahead N+1 failed.
7. End with a confirmed root cause, proof boundaries, a repair contract, and a regression-test contract.

Do not merge two different fault questions into one root cause. A vehicle can fail to act after valid route/MA restoration, while the automatic-cancel path independently fails because the Mission state never becomes error. State both, identify which one the RCA proves, and keep ADS-internal movement causes unconfirmed when ADS decision or traction logs are unavailable.

For Lilee Confluence pages, use the established `TL;DR → Issue → Video → Root Cause Analysis → Reproduce Steps → Repair Suggestions` skeleton. Put the TOC first under the Confluence house policy. Use code blocks for exact log and reproduction evidence, and use a native status control for confirmed RCA state.

## Interpretation guardrails

- Do not rely on a release name alone; prove code generation from logs or deployment metadata.
- Do not use vehicle-filtered logs as the complete WSS picture.
- Do not label every recheck as defective; show stale state, missed ADS exit, route churn, or a timeout.
- Treat retry count/duration as amplification, not root cause.
- Do not claim a specific facing signal stopped the vehicle without decoded MA or explicit facing-signal evidence.
- Keep authority validation intact; removing all WSS monitoring is not a safe repair.

### Route authorized while facing signal stays RED

When a vehicle is already stopped before an exact, repeated route timeout, test whether the timeout is a consequence of an unused route rather than the initiating fault:

1. Measure `first usable route/block authorization → first timeout` and compare later cycles. A fixed interval followed by rapid successful reauthorization is usually amplification.
2. Join route state with controlled blocks, facing-signal aspect, MA range refresh, and current-block exit. `Route AUTHORIZED` is not sufficient if the associated facing signal remains RED.
3. Find a close same-path comparator and align `route authorized → MA refresh → signal permissive → block exit`. Shared revoke/re-request churn is not the divergence if the comparator still moves.
4. Query raw WSS-agent DEBUG logs only with exact server-side node filters and short windows; full Modbus dumps saturate Loki quickly. Keep read-side actual state separate from write-side requested settings.
5. Check ADS-versus-WSS occupancy consistency. Record a current-block mismatch separately unless interlocking evidence proves it caused the signal failure.
6. Preserve the MA proof boundary: source may show that every dispatch refreshes signal state from WSS, but raw Type 3/Type 4 payloads and ADS/controller logs are required to prove the transmitted/accepted state and physical stop decision.

See `references/route-authorized-signal-red-stall.md` for the query pattern, comparator timeline, timeout classification, and proof boundary.

## Race-safe repair pattern

When authority revalidation overlaps ADS movement, fix **authority scope**, **event classification**, and **listener/FSM ordering** together. Timing delays and callback serialization do not make a stale ADS snapshot fresh.

1. **Separate the two windows.** MA calculation may include `current + forward` blocks, while the Nibble authority target contains only blocks not yet entered (`forward`). Do not classify the already-confirmed current occupied block as future movement authority merely because it appears in the MA range.
2. **Classify authority events directionally.** Route recheck is `AUTHORIZED → non-AUTHORIZED`; block recheck is `AUTHORIZED → non-AUTHORIZED`. Ignore occupancy-only, unchanged, and improving transitions. Filter route events through the forward authority context as well.
3. **Remove derived signal events, not independent safety inputs.** Signal state is derived from route/block state in this flow. Relevant TSR/bulletin changes independently alter forward authority and must remain monitored unless policy explicitly changes.
4. **Subscribe before snapshot.** Entering `ROUTE_REQUEST` or `MA_REFRESH` must register the ADS listener before reading current vehicle status.
5. **Keep the ADS listener across recheck cleanup.** Revalidation cleanup may remove route/block/bulletin listeners, but clearing the vehicle listener recreates the exit blind spot.
6. **Re-snapshot after awaited MA work.** Read ADS again immediately before moving from `MA_REFRESH`; this catches a tracker update whose async callback is queued.
7. **Reconcile block exit as normal progress.** If ADS confirms the Nibble block was exited during `ROUTE_REQUEST`, `MA_REFRESH`, or `AWAIT_BLOCK_EXIT`, transition to normal `COMPLETED`, cancel callback-raced state work when needed, centralize cleanup in the completed-state handler, and resolve the completion future only after cleanup. Do not fault Mission for normal progress.
8. **Use a single-winner lock only for commit arbitration.** Serialize ADS-exit and WSS-recheck commits, then recheck the FSM state under the lock. Do not treat the lock as an ADS-freshness mechanism, and do not add a redundant boolean guard when state plus lock already provide idempotency.
9. **Distinguish empty forward targets.** A terminal Nibble with no forward target completes normally; a nonterminal Nibble with an unexpectedly empty target retains `RouteRequestError` so malformed route/mission data cannot silently advance.
10. **Drain real failures.** For genuine Nibble errors, cancel and `gather(..., return_exceptions=True)` look-ahead tasks before transitioning Mission to failure.

## Repair validation

A safe candidate should:

- prove `MA window = current + forward` separately from `authority target = forward only`;
- ignore normal current-block release while retaining true forward route/block degradation detection;
- keep ADS position/block-exit processing active during authority revalidation;
- cover listener-before-snapshot and post-MA final-snapshot races;
- reconcile ADS-confirmed exit to normal completion from `ROUTE_REQUEST`, `MA_REFRESH`, and `AWAIT_BLOCK_EXIT`;
- serialize exit/recheck transition commits and prove only one completion winner;
- complete cleanup before resolving the normal completion future;
- preserve independent TSR/bulletin safety monitoring when signal-driven rechecks are removed;
- avoid requesting or revoking routes that WSS must reject because they contain occupied blocks;
- prove a route `WAIT` is actually awakened by a later route/block event and reevaluates;
- distinguish terminal empty targets from malformed nonterminal empty targets;
- verify Mission departure ordering and drain look-ahead tasks on genuine failure;
- supervise both current and look-ahead Nibble tasks so either failure immediately emits exactly one Mission `NIBBLE_EXECUTE_FAIL`, even while the other task remains pending;
- run formatting, focused async tests, the repository’s full build/test command, and a real ADS/WSS end-to-end movement test with MA/facing-signal verification.

## Review pitfalls

- Thalos tests use explicit `# Arrange`, `# Act`, and `# Assert` section comments as a coding convention. Add all three to every new or materially modified test, including async lifecycle and exception-path tests; blank-line grouping is not sufficient. Audit changed test functions rather than relying on visual spot checks.
- Do not reintroduce `COMPLETED_ABNORMAL` or `AuthorityViolationError` for an ADS-confirmed exit during authority validation. Under the forward-authority responsibility model, that exit is normal reconciliation; genuine route/MA failures still use the ordinary error states.
- A lock serializes competing callbacks but does not prove ADS freshness. Avoid fixed sleeps based on the nominal ADS report period; repair source scope and snapshot ordering instead.
- A race test is not concurrent merely because it invokes both paths. Block one path with events, start both tasks while the first remains suspended, then release it and assert the single winner.
- A look-ahead lifecycle test is incomplete if it covers only “current fails, look-ahead is canceled.” Add the inverse: current remains pending, look-ahead fails, Mission transitions once to `NIBBLE_EXECUTE_FAIL`, and all siblings are drained.
- Do not hand an independent reviewer the shorthand “only route/block triggers recheck” when TSR/bulletin authority monitoring is retained. State the exception explicitly.
- A test that mocks only the transition does not prove listener continuity or WAIT wakeup. Pair lifecycle unit tests with subscribe/snapshot races and one deterministic handler-loop probe.
- Treat build output as evidence only for the exact source revision that produced it. After review-driven edits, rerun the full build or compare a source-diff hash before and after; an earlier green background process is stale evidence.

## References

- `references/alpha-loki-stall-correlation.md` — saturation-safe Alpha Loki chunking, separation of initial route gating from long non-movement, same-path comparison, MQTT status-cadence checks, and ADS proof boundaries.
- `references/route-authorized-signal-red-stall.md` — classify fixed-interval route timeouts as consequence versus cause, join route/block/signal/MA evidence, filter high-volume raw WSS-agent dumps, separate read/write state, and preserve MA/ADS proof boundaries.
- `references/lookahead-nibble-metrics-cancel-blind-spot.md` — current/look-ahead task-error propagation into Mission state, watchdog cancel attribution, deterministic reproduction, repair contract, and missing inverse regression coverage.
- `references/corrected-window-late-departure.md` — reusable two-level attempt counting, schedule/route/signal/ADS segmentation, MAID-to-ACK checking, and filtered-export proof boundaries.
- `references/alpha-b5-late-departure-terminate.md` — timezone normalization, Loki saturation-safe filtering, signal-delay segmentation, and direct API/JPS/service-event cancellation joins from the 0.21b5 Alpha investigation.
- `references/mission-handoff-latency.md` — terminal-Nibble-to-parked/finalize/next-start segmentation, coordinator-gap falsification, external I/O attribution, and scheduled-hold interpretation.
- `references/stale-nibble-route-recheck.md` — concrete July 2026 Alpha evidence, query strategy, and the C2T→C1T→W1T Route 11 failure sequence.
- `references/authority-revalidation-repair.md` — forward-only authority responsibility, normal ADS exit reconciliation, Mission integration, and regression matrix.
- `references/pre-alpha-stop-risk-audit.md` — bounded topology, race-stress, WAIT-wakeup, departure/look-ahead, evidence-integrity, and go/no-go checks before field testing.
- `references/authorization-loss-provenance-triage.md` — distinguish TriOps occupancy input, Thalos route commands, and unattributable PLC/IXL/manual changes while preserving Type 7 provenance limits.
