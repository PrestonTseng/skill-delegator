# Stale Nibble route recheck: Alpha evidence pattern

This reference captures the reusable evidence and diagnosis from a July 2026 Alpha Thalos movement stall. It is a case study, not a permanent claim about every release.

## Correct-source discipline

The incident URLs were initially supplied with the wrong date and later corrected from 2026-07-24 to 2026-07-23. The corrected logs changed the conclusion from an older departure-timeout path to direct evidence of the 0.21b4 WSS recheck FSM.

Reusable rule:

- re-fetch corrected URLs rather than reusing downloaded data;
- label conclusions from the previous window as superseded;
- use FSM/log markers to verify the actual running code generation.

Corrected logs came from container `028ca081da1f` and contained `ROUTE_REQUEST`, `MA_REFRESH`, `AWAIT_BLOCK_EXIT`, and `Rechecking route authorization...`.

## Why two Loki views were required

Vehicle-filtered queries exposed mission and Nibble context, but omitted most global WSS agent events. The RCA required a second query over the same container and time window for:

```text
Updated WSS status route ...
Updated block ...
Updated signal ...
Requesting authorization for route ...
Revoking authorization for route ...
authorization/revocation confirmed
authorization/revocation timeout
```

Join both sets by Loki nanosecond timestamp.

## 215D direct sequence

Mission: `N2WS:T3W:1`.

1. `03:10:51.069` — C1T changed `FREE -> OCCUPIED` during normal C2T→C1T overlap.
2. Current C2T Nibble logged `Rechecking route authorization...` and transitioned `AWAIT_BLOCK_EXIT --(recheck)--> ROUTE_REQUEST`.
3. It classified C1T as occupied by something other than the vehicle and waited instead of completing on ADS movement.
4. `03:10:51.785` — ADS entered C1T, but the old C2T Nibble did not complete.
5. `03:10:54.757` — C2T changed `OCCUPIED -> FREE` and `AUTHORIZED -> UNAUTHORIZED`.
6. The stale C2T Nibble decided Route 11 was stale and revoked it.
7. `03:10:55.463` — Route 11 changed `AUTHORIZED -> CLEAR_ROUTE` while C1T remained occupied.
8. The live C1T Nibble rechecked and requested Route 11.
9. Route 11 controls C2T, C1T, and W1T. `03:11:00.685` — W1T became occupied.
10. WSS could not authorize Route 11. Stale C2T made 41 failed attempts; C1T made 120.
11. `03:24:53` — C1T entered `ROUTE_REQUEST_ERROR`; mission entered `NIBBLE_EXECUTE_ERROR`.

Causal chain:

```text
normal own-train overlap
-> over-broad WSS recheck
-> ADS block exit missed in ROUTE_REQUEST
-> stale old-block Nibble
-> normal release misread as stale authority
-> old route revoked/re-requested
-> train occupies a controlled block
-> WSS correctly rejects request
-> sustained stall and eventual mission fault
```

## Supporting and non-supporting vehicles

- 212D showed seven normal-change rechecks (C1T×1, W1T×2, W2T×4) and ultimately timed out waiting for W3T. It supports over-broad monitoring but does not show the same explicit Route 11 retry chain.
- 218D did not progress beyond mission lock in the supplied window and cannot support a movement-root-cause conclusion.

## Source checks that made the logs actionable

- Confirm route topology in `thalos/const/route.py`; Route 11 controls C2T, C1T, and W1T.
- Inspect `NibbleExecutor` listener lifecycle: `AWAIT_BLOCK_EXIT` receives ADS and WSS events; recheck transitions to `ROUTE_REQUEST`, whose waiting path can omit ADS position/block-exit processing.
- Verify authority evaluation’s treatment of the current vehicle’s occupied block versus WSS’s actual rule that an occupied route request is rejected.
- Use a deterministic probe for successive states. The relevant class of result is:

```text
next block occupied before ADS update -> WAIT
ADS updates while old block remains occupied -> WAIT
old block releases / route resets -> REQUEST stale route
```

## Proof boundary

The logs directly proved route revocation, repeated authorization failure, stale Nibble state, and mission fault. They did not include a decoded ADS MA payload proving the exact facing-signal ID/status at the physical stop. Report the former as established and the latter as requiring MA/ADS telemetry.

## Regression scenarios

1. ADS enters the next block while current Nibble is revalidating authority.
2. Old and new blocks are simultaneously occupied by the same train.
3. Old block releases and authorization changes after ADS has left it.
4. Two lookahead Nibbles evaluate/request the same route.
5. WSS rejects every route containing any occupied controlled block.
6. A route becomes authorized for one requester while another waits on an unchanged-state event.
7. End-to-end MA/facing-signal remains ahead and valid through C2T→C1T→W1T.
