# Mission completion and next-Mission handoff latency

## Why this reference exists

A vehicle can enter the terminal block well before ADS reports a parked state. Thalos completes the terminal Nibble on block entry, but Mission completion waits for `ATO_PARKED_ON_PLATFORM` or `PARKED_OUT_PLATFORM`, performs ADS/JPS finalization, then starts the next queued Mission. Operators may perceive this entire interval as a coordinator scheduling delay even when the queue handoff itself is immediate.

## Required timeline

Join exact nanosecond timestamps for both the prior and next Mission:

```text
prior terminal Nibble COMPLETED
-> Mission NIBBLE_EXECUTING -> ARRIVING
-> ADS parked status observed
-> ARRIVING -> FINALIZING
-> ADS mission-end notification
-> JPS Mission completion
-> FINALIZING -> COMPLETED
-> next Mission Starting mission execution
-> ADS_ALLOCATING -> ADS_ALLOCATED
-> ACTIVATING -> ACTIVATED
-> AWAIT_DEPARTURE -> door_close
-> ROUTE_AUTHORIZED -> DEPARTING
```

Compute these segments separately:

- terminal Nibble to `ARRIVING`;
- `ARRIVING` to parked/`FINALIZING`;
- `FINALIZING` to `COMPLETED`, split into ADS mission-end and JPS completion;
- prior `COMPLETED` to next `Starting mission execution`;
- next ADS allocation and activation;
- activated to door close (scheduled hold);
- door close to `DEPARTING` (route/FSM gate).

## Interpretation

- Terminal Nibble completion means the vehicle entered the terminal block; it does not prove it is physically parked.
- A 5–10 ms `COMPLETED -> next start` interval falsifies a coordinator queue-delay hypothesis even if visible departure occurs much later.
- Blank retry failures at a configured HTTP timeout boundary, followed by eventual success, support ADS/JPS latency; preserve the exact-exception proof boundary if the exception type is not logged.
- Read the scheduled departure-delay calculation before treating `ACTIVATED -> door_close` as lateness. This interval can be intentional.
- Do not combine parked wait, finalization I/O, next allocation, scheduled hold, route readiness, and actual departure into one opaque “Mission handoff” duration.

## Alpha 0.21b5 example

Corrected UTC window: `2026-07-28T17:50:00Z–19:00:00Z`.

`0101U -> 101D`:

- last Nibble to prior completion: 12.112 s;
- parked wait: 11.994 s;
- finalizing: 0.116 s;
- prior completion to next start: 0.010 s;
- next ADS allocation: 12.229 s;
- scheduled hold: 35.006 s;
- last Nibble to next `DEPARTING`: 59.710 s.

`0102U -> 102D`:

- last Nibble to prior completion: 19.089 s;
- parked wait: 12.169 s;
- finalizing: 6.919 s (4.020 s ADS mission-end plus 2.899 s JPS completion);
- prior completion to next start: 0.005 s;
- next ADS allocation: 13.498 s;
- next start to activation: 16.268 s;
- scheduled hold: 36.006 s;
- last Nibble to next `DEPARTING`: 71.706 s.

The queue handoff was not the delay. The perceived delay was parked confirmation, external ADS/JPS I/O, and scheduled departure hold.
