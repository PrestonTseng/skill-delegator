# TSR Behavioral Specification — Confirmed Decisions

Captured from Preston's review session (2026-05-21). These are authoritative behavioral decisions for the TSR feature (Phase 1 + Phase 2 Form B). Consult before writing any TSR-related story AC, design doc, or test plan.

> **Supersession note (2026-06-15 spec revision):** use the live Confluence spec as the final source of truth when this reference conflicts with it. In particular, the current spec revision removed the pre-enforcement in-zone check from the backlog split, uses the approve/pending Form B model, and no longer treats reject / retry / MMS-offline handling as active mainline story slices in the backlog page.

---

## Status Model

- **Only `Effective` status triggers operational effect.** `Scheduled` = StartTime not yet reached; no operational effect on vehicles.
- `StartTime` omitted → effective immediately (treat as `0`).
- `EndTime` omitted → active indefinitely (treat as `∞`).
- Overlap check covers both `Scheduled` + `Effective` states.

## Mission Fault Boundary

- **TSR never causes a mission fault directly.**
- Vehicle holds at zone boundary → ADS nibble/mission timeout fires → that's the fault trigger, not TSR.
- A "Blocked" rejection = no mission fault, no auto-retry. Relies on nibble/mission timer to naturally end the mission.

## SS / MMS Offline Behavior

- SS is the **golden copy** for everything: vehicle position, bulletin state, zone occupancy.
- MMS offline: SS auto **Retry-able reject loop** — no Blocked escalation, no mission fault.
- SS continues operating with the last known bulletin state while MMS is offline.

## Pre-Enforcement Vehicle-in-Zone Warning

Flow when dispatcher tries to turn enforcement ON:
1. MMS sends `GET bulletin/{id}` to SS.
2. SS responds with `vehicles_in_zone[]`.
3. Non-empty → MMS shows a **blocking confirm dialog** before sending the enforcement ON request.
4. Empty → MMS sends enforcement ON request directly.

Do NOT add a `force: true` flag to the enforcement request. The confirm dialog is the UX gate.

## Block Max Speed vs. Bulletin Speed Limit

- **Bulletin priority wins.** A bulletin speed limit can legally exceed the block max speed.
- Block max speed is an **advisory warning** and never blocks or rejects the bulletin.
- Current Jira requirements (SART-1865 / SART-1933, revised 2026-07-29) require operator warnings during both bulletin creation and Enforcement ON; the live Jira/spec remains authoritative if this scope changes.
- Startup/max-speed-update re-validation logs warning mismatches only; it does not notify the dispatcher or automatically invalidate a bulletin.

## Form B Authorization

- Authorization not granted → vehicle holds at zone boundary.
- No mission fault issued by TSR. ADS nibble/mission timeout handles natural end of mission.

## Signal-Based Authorization

- Signal-based auth = **milepost selection constraint on UI**, not a separate authorization engine.
- Architecture is identical to MA-based; only the milepost options are scoped to signal positions.
- Supports traditional railway customers without requiring a different code path.

## N+1 / N+2 Lookahead

- **N+2 is out of scope.**
- N+1 window is a **configurable parameter** (default: 1). Adjustable without code change.

## Mission Path IDs

- `T3W:S2WN:2` (and similar) = **static mission path ID** — for human readability only.
- **Runtime authorization uses UUID.** All inter-service references at execution time use UUID.

## Story 13 — Retry Interval

- Two-tier: **site global default** + **dispatcher per-rejection override**.
- Dispatcher can adjust retry interval for a specific rejection without changing the global setting.

## Story 11 — ETA Column

- **ETA column is removed.** Cannot calculate ETA without vehicle speed data in MMS at this time.

## DOM9 — Zero-Extension MA

- SS issues: end milepost = vehicle's current position (zero-extension MA).
- **No ADS ACK required.** ADS applies braking curve immediately.
- This is a Direct MA constraint; ADS treats it as authoritative.

## Line vs. Track Terminology

- **Line** = route/line (e.g., Tamsui Line, Bannan Line).
- **Track** = specific rail (e.g., northbound vs. southbound track in a dual-track corridor).
- Use consistently in all story AC and UI copy.

## ICD Reference

- ICD Type-03, field 17 = `TSR` — List of TSR settings.
- Confirm exact schema at http://10.2.10.51/icd/latest/ before implementation.

---

*Source: TSR Backlog Confluence review session, Preston + Jacob, 2026-05-21. Applies to SafeART TSR Epic (SART Confluence space).*
