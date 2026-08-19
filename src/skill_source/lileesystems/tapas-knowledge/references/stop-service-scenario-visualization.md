# Stop-service scenario visualization for PO/design review

Use this when explaining TrackMap / mission-definition stop-service semantics to a product or planning audience.

## Recommended figure pair

For a single scenario, show **both** views together:

1. **Stop timeline view**
   - Show the service window explicitly: `start -> depart` or `arrive -> end`.
   - Attach the mission-definition fields directly to that window:
     - `service_type`
     - `door_operation_required`
     - `door_side`
     - `psd_required`
     - `dwell_time`
     - `control_mode` (optional metadata only)
   - Purpose: explain what the schedule / mission model needs to carry.

2. **Responsibility swimlane view**
   - Separate responsibility by layer:
     - **JPS / Mission Definition** = defines timing + stop-service fields
     - **SS** = evaluates readiness / release conditions and advances mission state
     - **ADS / train-side / station-side systems** = execute physical door / PSD behavior
   - Purpose: prevent readers from inferring that JPS or SS directly actuate doors.

## When to use

Use the pair when a textual scenario alone is likely to blur the boundary between:
- schedule intent,
- mission-state progression,
- physical door / PSD execution.

## Scenario 1 example

**Passenger platform departure with boarding door configuration**

Timeline example:
- service window: `start -> depart`
- `service_type = board`
- `door_operation_required = true`
- `door_side = left | right | both | auto | unknown`
- `psd_required = true | false | unknown`
- `dwell_time = configured service window before departure`
- `control_mode = optional metadata only; not scheduling semantics`

Swimlane message:
- JPS defines the stop-service intent.
- SS decides when the configured conditions are satisfied.
- Downstream train/station systems perform the physical open/close / PSD behavior.

## Why this format works

- The timeline answers: **what was added to the data model?**
- The swimlane answers: **who owns which part of the behavior?**
- Together they reduce the most common PO confusion: mistaking stop-service semantics for low-level door control.
