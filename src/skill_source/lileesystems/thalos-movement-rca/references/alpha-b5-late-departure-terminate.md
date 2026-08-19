# Alpha 0.21b5 late-departure and Mission-terminate investigation

## Why this reference exists

This case adds two reusable Thalos RCA lessons: user-supplied Loki timestamps must be normalized before querying, and a reported "terminate API error" may cross three distinct cancellation paths whose logs have different meanings.

## Time and release normalization

The reported browser window was `2026-07-29 01:50–03:00` in UTC+8. Its authoritative UTC query window was:

```text
2026-07-28T17:50:00Z–19:00:00Z
```

Do not infer timezone from an API URL alone. Record both the user-facing time and normalized UTC range, verify the conversion with a time tool, and explicitly supersede any conclusions drawn from the wrong window.

Release boundaries were established from startup logs rather than the release label alone:

```text
0.21b5 first startup: 2026-07-28T09:38:30Z
0.21b5 restart:       2026-07-28T11:52:17Z
rollback to 0.21b2:   2026-07-29T00:51:03Z
```

The `safeart-0.21b5` tag mapped to revision `42034d2ce1dae784c74324279287962866bb2520`.

## Loki collection pattern

A broad query reached the 5,000-entry limit and covered only part of the requested interval. Treat any result at the limit as truncated evidence.

Use unsaturated server-side filters in parallel, for example:

```text
terminate/error:
  terminat | failed to cancel service | task exception | traceback |
  invalid transition | mission activation failed | service removed event

movement/departure:
  authorize vehicle departure | mission departing | mission departed |
  departure command | facing signal | scheduled mission | await_departure

API/cancel:
  /cancel | mission-execution | cancelling mission with mission_uuid |
  successfully cancelled mission | cancel mission on JPS | service removed event
```

Preserve nanosecond timestamps, sort them globally, and join by Mission UUID, service ID, and vehicle ID.

## Late-departure evidence pattern

For Mission `106D.N2WS:T3W:1`:

```text
18:23:13.714Z  ROUTE_AUTHORIZED -> DEPARTING
18:23:13.725Z  facing signal 3L not GREEN, attempt 1
18:23:18.725Z  facing signal 3L not GREEN, attempt 2
18:23:23.725Z  departure command issued
18:23:30.152Z  DEPARTING -> DEPARTED
```

This proved a 10.011-second signal-aspect delay between entering `DEPARTING` and issuing the departure command, and 16.438 seconds to `DEPARTED`. The facing ID was correct (`3L`), so this case was not evidence of stale facing IDs. Do not generalize one signal-delayed Mission to all late departures; separately measure schedule/door, route readiness, departure authorization, command dispatch, and ADS movement/acknowledgement.

## Mission cancellation paths

Always separate these paths:

1. **Direct Thalos API cancellation** — `/api/v1/mission-execution/{uuid}/cancel` calls the coordinator and may return 404/409/500 or log success.
2. **MissionExecutor cleanup call to JPS** — termination may call the JPS Mission cancel endpoint and retry timeouts or `409 Conflict`.
3. **JPS service-removed event back to Thalos** — the event listener calls coordinator cancellation again; the executor may already be cleaned up or finalizing, producing `not found` or `cannot be cancelled` logs.

A later internal error does not prove the original API caller received an error. Join these markers for each UUID:

```text
Cancelling mission with mission_uuid
Terminating mission execution
Attempting to cancel mission on JPS
HTTP status from JPS
Mission terminated
Successfully cancelled mission with mission_uuid
Service removed event received
Failed to cancel service
```

In this case, multiple direct Thalos API cancellation flows logged success even when internal JPS cancellation timed out or returned 409. Later service-removed events then produced duplicate-cancel errors for already-cleaned/finalizing executors. Preserve the proof boundary until access-log status or caller response confirms a client-visible failure.

Corrected-window direct API accounting was:

- 53 request-start logs across 52 unique Mission IDs;
- 51 server-side successes;
- one repeated request mapped by source to 404 after prior cleanup;
- one request crossing the 19:00Z query boundary;
- no direct Thalos 409 or 500 observed.

Successful endpoint latency was 0.089–36.612 seconds, median 13.594 seconds. Of 51 successes, 29 exceeded 10 seconds, 25 exceeded 15 seconds, 19 exceeded 20 seconds, and 9 exceeded 30 seconds. This demonstrates why threshold counts matter: a caller with a shorter timeout can report failure even though Thalos later logs success. It does not prove the caller timeout without its configuration or raw response.

## Lock-timer noise versus causality

Repeated `Invalid transition: LOCKING --(lock)--> ?` errors can dominate counts. Determine whether they precede and delay the affected operation or are stale/retried background timers. Do not treat their volume as proof that they caused API cancellation or departure delay.
