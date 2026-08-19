# Door vs PSD control study (TAPAS design boundary)

Use this note when discussing mission timing, stop-service semantics, door control, or PSD coordination in TAPAS.

## Core conclusion

TAPAS should model **service intent** and **dwell / stop timing**, not low-level physical door actuation.

Clean boundary:
- **JPS / mission definition** — stop-service intent and timing semantics
- **SS** — evaluates readiness / release conditions for mission progression
- **ADS / station-side PSD systems** — execute actual door / PSD behavior
- **Interlocking / authority chain** — movement authority, route conflict prevention, locking
- **MMS / CTC override** — abnormal / supervised override path only

## Recommended mission-definition semantics

Prefer stop-level service fields such as:
- `service_type`: `none | board | alight | board_alight | technical_stop`
- `door_operation_required`: `true | false`
- `door_side`: `left | right | both | auto | unknown`
- `psd_required`: `true | false | unknown`
- `dwell_time`: service / exchange window duration
- optional `control_mode` metadata: `manual_crew | train_automatic | train_plus_psd | remote_supervised`

## Recommended wording for backlog/design docs

When item wording says "buffer time" or "door behavior," check whether the real need is stronger:
- replace **buffer time** with **stop-service timing** or **service dwell window**
- replace **door behavior** with **stop-service semantics** unless low-level actuation is truly in scope

Avoid wording that implies:
- movement authority itself contains physical door commands
- SS is the physical door executor
- AV1 / yard-handling stops should inherit passenger-door semantics by default

## Practical interpretation for mission timing

- `start -> depart` = origin service dwell / boarding window
- `arrive -> end` = terminal or stop-end service dwell / release window
- arrival does **not** imply immediate mission end
- passenger alighting after arrival should **not** depend on the next mission starting
- non-passenger stops may still require arrival-side handling time without passenger-door semantics

## Abnormal handling

Forced open/close from control center belongs to a separate abnormal / override path. Keep it out of normal mission-scheduling semantics unless the design explicitly covers authorization, safety preconditions, and audit logging.
