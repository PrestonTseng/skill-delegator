# Seshat 2.0 Planning Notes

Use when shaping Seshat 2.0 specs, delivery maps, or tickets. This is a condensed planning reference from the July 2026 Seshat 2.0 spec/delivery-map work; the live Confluence spec remains source of truth.

## Source pages

- Spec / backlog: `Backlog - Seshat 2.0` — Confluence page `3713728564`.
- Delivery map: `Seshat 2.0` — Confluence page `3826581575`.
- Existing PoC epic: `SART-1769`.
- Existing PoC backend/frontend/performance reference tickets: `SART-1770`, `SART-1790`, `SART-1777`.
- Concrete debug use case: `SART-1858`.

## Stable framing

- Seshat 2.0 is an engineering observability / replay / debug platform for TAPAS MQTT traffic.
- Seshat is **not** a TAPAS runtime dependency. TAPAS services must continue operating if Seshat is unavailable.
- The existing Go/React Seshat-Go PoC remains available during transition.
- New frontend work initially targets the current PoC API through historical visualization work.
- Backend replacement comes later and should not retire the PoC until it supports required Phase 3 capabilities and integrates with the new frontend.
- Avoid promising “all MQTT topics” until the capture policy is defined: broker wildcard vs configurable topic set vs required-topic allowlist.

## Spec style Preston prefers for Seshat

- Simpler than the TSR spec when possible: concise, precise, concrete.
- Keep only sections that help engineers / QA / PO judge scope, acceptance, or dependencies.
- Formal Confluence artifact language: English.
- Conversation with Preston: Chinese.

## Phase / workstream model

1. Phase 0 — Existing PoC baseline and transition control.
2. Phase 1 — Frontend baseline parity against current PoC API.
3. Phase 2 — Historical query, payload filtering, and ICD-aware display.
4. Phase 3 — Historical multi-topic comparison and signaling correlation.
5. Phase 3 — Mission / MA timeline analysis.
6. Phase 3 — Trackmap replay foundation.
7. Phase 4 — Pre-alpha testbed integration, after historical visualization is useful.
8. Phase 5 — Backend replacement integration.
9. Phase 6 — Realtime monitoring mode.
10. Phase 7 — Rule-based anomaly detection framework.

## Realtime / historical coexistence

Realtime monitoring is a live view over the same ingestion/storage model used by historical analysis, not a second source of truth.

- All consumed MQTT messages are persisted into TimescaleDB.
- Historical mode reads persisted data by fixed start/end time range.
- Realtime mode shows a rolling window ending at now.
- Paused realtime mode freezes the current live window for inspection as a historical interval.
- If the frontend disconnects or falls behind, recovery is by querying the affected time range historically.

## Mission / MA timeline analysis

Preferred framing: `Mission / MA timeline analysis`, not just `MA analysis`, because the useful view correlates mission plan, mission execution, MA context, and vehicle behavior.

Inputs:

- Type 17 — Vehicle Service Instructions v2: planned mission timing such as start time, departure time, arrival time, and end time.
- Type 18 — Vehicle Service Instruction Execution Status v2: mission execution status updates.
- Type 3 — SS Movement Authority: includes the **virtual MA departure signal** that tells the vehicle it may leave the platform.
- Type 2 — ADS Vehicle Status: vehicle speed and position during mission execution.

Important boundary:

- The MA departure signal is a virtual signal contained in Type 3 MA.
- It is **not** the physical wayside signal state from Type 7 WSS Status.
- Do not model or word it as a Type 7 / wayside signal condition unless Preston explicitly changes the source-of-truth decision.

Timeline markers to support:

1. Mission state transition Scheduled → Locked.
2. Mission state transition Locked → Active.
3. MA departure signal becomes green / ready for departure.
4. ADS speed record during mission execution.
5. Mission state transition Active → Completed.

Open design issue:

- Define correlation key across Type 17, Type 18, Type 3, and Type 2: mission UUID, vehicle ID, service ID, train ID, route ID, timestamp window, or combination.

## Rule-based anomaly detection framing

- Include as a later-phase capability, not Phase 1 acceptance.
- Start with a rule contract: input topics, correlation key, time window, expected behavior, anomaly condition, output severity, false-positive handling, and execution mode.
- A rule can declare historical execution, realtime execution, or both.
- Rule outputs should start as findings / annotations on query or visualization results.
- Do not imply OCC/product alerting until an alert destination and operational response are explicitly designed.
