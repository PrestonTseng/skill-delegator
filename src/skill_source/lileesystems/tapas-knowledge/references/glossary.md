# TAPAS Glossary

Stable cross-service domain terms. Not exhaustive; expand as new terms appear.

## Mission, Service, Trip — the scheduling unit hierarchy

- **Mission** — Single execution unit on Safety Server. One scheduled run from origin block to destination block. Identified by a Mission ID like `M5 (N2WS:T3W:2)` (origin:destination:variant). Executed by a Mission Executor following the Mission FSM.
  - **M5 Mission FSM states:** Scheduled / Locked / Active / Completed / Canceled.
- **Service** — A pair (or set) of missions that together form a "run" — typically an outbound + inbound pairing. E.g., Service 127 has Mission 127U (up) and Mission 127D (down). **Service ID** is referred to as 班次 in Chinese context.
  - Note the overload: do not confuse with "service" meaning microservice.
- **Trip** — A combination of one or two missions, identified by a Trip ID (3-digit number per ICD Definitions, e.g. `001 (N2WN:T3W:1, T3W:S2WS:2)`). Trip IDs are referenced in MA payloads.
- **Nibble** — Subdivision of a Mission. Each Nibble represents a small section of the route, executed by a Nibble Executor under its parent Mission. Updates the vehicle's Movement Authority block by block.

## Track topology

- **Block** — A trackside segment with controlled access. Has occupancy state (free / authorized / occupied). Tracked in WSS via `BlockStat`. Block IDs look like `H1T`, `C1T`, `T3W`.
- **Sub-block** — Subdivision of a block (e.g. `C1T1`, `C1T2` if `C1T` has 4 sub-blocks). Used for finer-grained vehicle position reporting.
- **Lane** — Track lane identifier. Common values: `NT` (North Track), `ST` (South Track).
- **Route** — A path through one or more blocks. Vehicles request route authorization to enter. Routes are identified by route IDs (numeric).
- **Direction** — `0` = Increasing / Downward, `1` = Decreasing / Upward (relative to milepost).
- **MP (Milepost)** — Position reference on the track, formatted like `1K+301`. Encoded as 5-digit value with 1/10 MP precision (`1K+301 = 13010`). Used in TSR segment definitions, MA boundaries (`StartMp` / `EndMp`), and Nibble boundaries.

## Movement Authority

- **MA (Movement Authority)** — Permission given to a vehicle to move within a defined boundary. Sent from Safety Server to ADS. Each connected vehicle has an MA managed by SS's MA Manager; MA is auto-created on connect and auto-cleared on disconnect.
  - Carries: `MAID`, `VehicleId`, `ServiceId`, `StartTime` / `EndTime`, `TripId`, `RouteList`, `AuthorizedDir`, `OperationMode`, `AuthorizedSpeed`, facing-signal info, door-control timing, milepost bounds, and optional TSR list.
- **MA ACK** — Vehicle's response to a sent MA (Type 4). Track ACK status to detect MA rejections. Status codes: 1 = OK, 2 = Invalid values, 3 = Expired, etc. (see ICD).
- **SS MA ACK** — SS's acknowledgement that it received the ADS MA ACK (Type 5).
- **MA FIN ACK** — Vehicle's notification that the MA has been finalized / completed (Type 6).
- **Applied MA** — Currently active MA on the vehicle (`AppliedMAId` field in Vehicle Status).

## Operation modes

ADS Operation Mode enum (used in MA `OperationMode` and Vehicle Status `OperationMode`):

| Value | Name | Meaning |
|-------|------|---------|
| 1 | ATO-NORMAL | 一般自駕 |
| 2 | ATO-DGRADED | 自駕降級 |
| 3 | ATO-DISENGAGE | 自駕解除 |
| 4 | ATO-AOB | 自駕避障 |
| 5 | ATO-STOP | 自駕停車 |

## Vehicle states

Vehicle Running Status enum (`VehicleStatus` field in Type 2):

| Value | Name |
|-------|------|
| 0 | INIT |
| 1 | SHUNT (Manual, user cutoff) |
| 2 | PARKED (Manual, Zero Speed) |
| 4 | PARKED (ATO, Zero Speed, Outside Platform) |
| 5 | PARKED (ATO, Zero Speed, On Platform) |
| 6 | READYTOGO (ATO, Wait new Trip) |
| 7 | AUTHORIZED |
| 8 | DOORIXL (ATO, in door interlocking operation) |

## DOM, degradation, and recovery

- **DOM (Degraded Operation Mode)** — Severity levels Mode 1 through Mode 10 indicating vehicle / system degradation. Defined in ADS 3.26 (Confluence AV space, page 3668511419).

  Three driving performance dimensions, each with 4 degradation levels:
  - **Proceeding Distance:** follow latest MA → follow last MA → as short as possible → not moving
  - **Speed:** predefined path → ≤75% speed limit (≤30 km/h on 40 km/h lines) → 5 km/h → 0 km/h
  - **Deceleration:** predefined path → soft brake (-0.98 m/s²) → hard brake (-2.45 m/s²) → emergency brake (-4.9 m/s²)

  Mode summary (triggering source: V = Vehicle self-triggered, CC = Control Center / SS command):

  - **Mode 1** — No driving change; alert to CC for minor non-safety device issues. (CC)
  - **Mode 2** — Latest MA, ≤75% speed limit, soft decel if over limit. (CC or V)
  - **Mode 3** — Latest MA, ≤5 km/h, soft decel if over limit. (CC or V)
  - **Mode 4** — Last MA, predefined speed, stop before MA boundary, resume on SS reconnect. (V)
  - **Mode 5** — Last MA, ≤75% speed limit, stop before MA boundary, resume on SS reconnect. (V)
  - **Mode 6** — Last MA, ≤5 km/h, stop before MA boundary, resume on SS reconnect. (V)
  - **Mode 7** — Decelerate to stop (-0.98 m/s²); proceed only after CC releases. (CC or V)
  - **Mode 8** — Decelerate to stop (-2.45 m/s²); proceed only after CC releases. (CC or V)
  - **Mode 9** — Emergency brake to stop (-4.9 m/s²); proceed only after CC releases. (CC or V)
  - **Mode 10** — Emergency brake (-4.9 m/s²) + handbrake + park gear; requires hardware button or CC override to recover. Full breakdown — triggers Faramund recovery flow. (CC or V)

  **Emergency stop coverage:** TAPAS has no standalone Emergency Halt Bulletin type. Emergency stop capability is covered jointly by DOM Mode 7–10 (per-vehicle) and Form A Bulletin (per-segment). Together they are equivalent to a traditional railway Emergency Halt Order.

- **Felicia** — Vehicle dispatcher controlled by Faramund during DOM 10 recovery. Faramund ↔ Felicia communicate over WebSocket using D0–D4 (down / dispatcher → Felicia) and U0–U7 (up / Felicia → dispatcher) message types.

## ARK Code

- **ARK Code** — Coded event identifier for monitoring system behaviour in real time. Originally an ACES Team design.
- **In production**, ARK Codes are **embedded as `ArkCodeQueues` sub-fields inside Type 2 (ADS Vehicle Status) and Type 19 (TriOps Status)** — they are *not* a separate MQTT topic.
- `QualifiedArkCodeId` format: `<source_tag>:<code_id_hex_string[2:]>`. Example: code `0x03050103` published by `/block_occupancy_health_monitoring/false_positive` becomes `/block_occupancy_health_monitoring/false_positive:03050103`.
- **Cloud Team's parallel ARK Code system** — a Cloud-Team-internal ARK Code system for SS / SE / JPS / MMS, with categories `error / warning / state / command / downgrade / audit` and a proposed broker pattern `ark_code/<service>/<code_id_path>`. **Status: still in backlog, not implemented.** Do not assume the broker pattern exists in production.

## VSI / VSIES

- **VSI (Vehicle Service Instructions)** — The schedule message published by MMS that instructs SS what to run. ICD types: Type 11 (deprecated) → **Type 17 (VSI-v2)**. The v2 mirrors HTTP delivery (JPS → SS) onto MQTT for downstream consumers.
- **VSIES (VSI Execution Status)** — Execution status feedback published by SS. ICD types: Type 12 (deprecated) → **Type 18 (VSIES-v2)**. The v2 mirrors HTTP delivery (SS → JPS) onto MQTT.
- **班次** — Chinese term for Service / Service ID, used interchangeably in docs.

## M-number legend (SafeART Web UI feature modules)

M-numbers are **feature module labels** used in the SafeART web application (Faramund / MMS frontend). They appear on UI screens, in Jira tickets, and in Confluence docs to identify which part of the app a change or defect belongs to. Authoritative source: [Page Routes](https://lileesystems.atlassian.net/wiki/spaces/SART/pages/2801598472/Page+Routes).

| M-number | Feature name (EN / ZH) | Primary route(s) | Notes |
|----------|------------------------|------------------|-------|
| **M1** | Track Map — Line 1 | `/login/map` → `/orientation` → `/m1` | Read-only track map, all roles |
| **M2** | Track Map — Line 2 | `/m2` | Same login flow as M1 |
| **M3** | Track Map — Line 3 | `/m3` | Same login flow as M1 |
| **M5** | Real-Time Schedule / 即時班表 | `/schedule` | Admin, Manager, Operator only; Analyst redirects to /report, Monitor to /profile |
| **M5 (Schedule Plan)** | Schedule Plan / 排班計畫 | `/plan` | Month View + Day View; sub-feature of M5 |
| **M5 (Preview)** | Preview Schedule / 預覽班表 | `/plan/preview` | CRUD table; sub-feature of M5 |
| **M6.a** | Override / 超越控制 | `/override` | Admin, Manager, Operator |
| **M6.b** | Safety Event / 告警事件 | `/event` | Admin, Manager, Operator, Analyst |
| **M6.c** | Vehicle Management / 車輛管理 | `/vehicle` | Admin, Manager, Operator |
| **M6.d** | Report / 每日報告 | `/report` | Admin, Manager, Operator, Analyst |
| **M8** | (uses M5-M8 login flow) | `/login` | M8 shares the same login entry point as M5-M7 |
| **UM** | User Management / 帳號管理 | `/user` | Admin, Manager only |
| **AUDIT** | Audit / 簽核決策 | `/audit` | Admin, Manager only |

**Login flows:**
- M5–M8 login → `/login` → `/schedule` after auth
- M1–M3 login → `/login/map` → `/orientation` → `/m1`, `/m2`, or `/m3`

**Role-based redirect rules (post-login):**
- Analyst → `/report`; Monitor → `/profile`; Admin / Manager / Operator → `/schedule`

> ⚠️ Do not confuse M-number module labels (web UI features) with Mission IDs like `M5 (N2WS:T3W:2)` (scheduling units on Safety Server). Both use "M5" but refer to completely different concepts. Context disambiguates.

## Operator-facing concepts

- **Manual Mode** — Operator-controlled mode in MMS where missions can be cancelled / dispatched manually. Has its own state machine. **M5 / M6.a** are MMS Manual Mode features (M6.a was the "cancel today's services" capability; cross-day cancel was added in 0.18).
- **TSR (Temporary Speed Restriction)** — Umbrella term for all Bulletin types in TAPAS. Created by OCC Dispatcher in MMS, goes through JPS → SS, integrated into MA so ADS obeys automatically. Source of truth: SART Confluence "Backlog - Temporary Speed Restriction (TSR)" (page 3714482215).

  **Three Bulletin Types (canonical names — use these everywhere):**
  - **TSR** — Speed restriction only. SS includes a speed limit in MA; ADS must not exceed it while in the zone. No stop required.
  - **Form A** — No entry (禁止進入). SS does NOT extend MA into the zone. ADS stops at the last authorized block and waits until the bulletin expires or enforcement is toggled off.
  - **Form B** — Stop → request authorization → approved → enter at restricted speed. SS creates a pending authorization per vehicle/mission. Dispatcher approves or rejects via MMS queue. Authorization scoped to `(vehicle_id, mission_id, entry_sequence)`; consumed on exit. *(Phase 2 — not yet implemented.)*

  > **Naming:** Form A / Form B / TSR are the only correct names. The cross-team aliases Type-A / Type-B / Type-C have been **retired** — do not reintroduce them in docs, tickets, or conversation.

  **Architecture:**
  - SS holds the golden copy of all operationally active TSR data.
  - JPS is the API gateway; all MMS TSR operations go through JPS → SS.
  - Timer-driven state transitions (Scheduled → Effective → Expired) are owned by SS.
  - JPS persists historical records and audit logs.

  **Status model:** Not Enforced → (Enforcement ON) → Scheduled (if StartTime in future) → Effective → Expired.
  Enforcement toggle is the primary gate — no operational effect until ON.

  **StartTime / EndTime are optional:**
  - StartTime omitted → bulletin takes effect immediately when enforcement is toggled ON (becomes Effective immediately, not Scheduled).
  - EndTime omitted → bulletin remains active indefinitely until enforcement is toggled OFF.

  **Mid-zone activation — MA truncation mechanics (downtrack direction):**
  When a bulletin becomes Effective while a vehicle is already inside the zone, SS applies a two-step truncation:
  1. Set MA `EndMP` = bulletin `FromMP` (zone entry boundary).
  2. If the result violates the directional constraint (`EndMP < StartMP` for downtrack), set `StartMP` = `FromMP` as well → MA becomes `[FromMP → FromMP]` (zero-length).
  SS *also* sends DOM9 independently to stop the vehicle — the MA truncation alone cannot push the vehicle backward.
  Uptrack direction: constraint is `EndMP > StartMP` (reversed); same two-step logic applies with mirrored inequality.

  **N+1 Lookahead — Form B authorization gate:**
  Before a vehicle departs the station, SS pre-creates Form B authorization requests for every Form B zone in the route; dispatcher queue is populated in advance.
  At each block transition, SS evaluates block N+1 and N+2:
  - No bulletin → normal MA extension.
  - TSR → normal MA extension with speed limit applied.
  - Form A → MA extended only to Form A boundary; vehicle waits.
  - Form B at N+2 → pre-create authorization (entry_seq) and add to dispatcher queue as early warning; not yet gating MA.
  - Form B at N+1 → gate check: if approved, extend MA into zone at speed limit; if not approved, MA extended only to Form B boundary; vehicle waits.
  **N+2 is a configurable lookahead depth parameter** — not a hard architectural limit. Once N+1 behavior is confirmed stable, the lookahead can be extended to N+3 or deeper via site-configurable parameter.

  **MMS / JPS offline — degraded mode:** SS continues operating on last known bulletin state (golden copy on SS). SS does not pause MA push or halt enforcement on disconnection. Pending Form B authorization requests cannot be approved. SS applies timeout-and-escalation: after `T_timeout` (default 30s) → auto Retry-able reject; after `max_retries` → Blocked reject; vehicle waits at boundary. `T_timeout`, `T_retry`, `max_retries` are site-configurable.

  **DOM9 — Emergency Stop Command:** Type 9 Vehicle Command sent by SS to ADS. Instructs vehicle to emergency-brake to a standstill regardless of current MA. Used exclusively in mid-zone activation (Path 9): when enforcement is turned ON while a vehicle is already inside the zone, SS truncates MA to zero-length AND sends DOM9 as a safety backstop. DOM9 is NOT used in normal entry-prevention (vehicle stops naturally at boundary when MA is not extended).

  **Mission path ID vs instance UUID:** Mission IDs like `T3W:S2WN:2` are static route path identifiers (template/path). Actual running instances are distinguished by UUID at the SS level. Dispatcher-facing displays show the path ID as a human-readable hint; SS authorization is always scoped to the instance UUID.

  **ICD Type 03 MA — TSR field:** Field 17 `TSR` carries `List of TSR settings`. Reference: http://10.2.10.51/icd/latest/type-03-ma. No new MA fields are required for Form A, Form B, or TSR bulletin types.

  **Known design gap:** Modifying EndTime while Effective requires toggling enforcement OFF first, creating a brief window where Form A/Form B protection lapses. Proposed fix: allow EndTime-only edits while Enforced without requiring a not-enforced cycle. Not yet resolved (as of 2026-05).
  - **Immediate TSR** — active on approval, no scheduled start.
  - Fields include segment (`FromMP` / `ToMP` / `LaneId`), `SpeedLimit`, `Mode`, `StartTime` / `EndTime`, `BrakingCurveNum`.
- **Yard** — Vehicle storage / start-of-day location. Vehicles dispatch from yard, return to yard.
- **OCC (Operations Control Center)** — Where operators monitor the system. MMS is the primary OCC interface. OCC frontends do **not** subscribe to the MQTT broker directly.
- **CTC** — Centralized Traffic Control (used in field names like `VehicleDoorCtrl` notes that reference "CTC set time value").

## Signal & route

- **IXL (Interlocking)** — Trackside interlocking logic that authorizes routes. Reported in WSS Status `RouteStat` as `IXLRouteStat`.
- **FacingSig / FacingSigStat** — The signal a vehicle is facing in its authorized direction (e.g. `6R`) and its aspect value.
- **Signal Aspect** — Numeric value indicating signal state (green / red / etc., per IXL convention).
- **AreaOutOfService** — Vehicle location when not on a service block. Enum values: `0` ON-SERVICE-LINE, `1`/`2` AV-1/AV-2 (avoidance areas), `11–14` CHARGE areas, `21–26` PARK areas, `31` MAINTENANCE-1, `41` WASHING-1.

## Identifiers

- **VehicleId / AssetId** — Vehicle unique ID, e.g. `ADS-0001`. **VehicleId equals AssetId.**
- **asset_id (service/container instance)** — Unique identifier of a publishing SafeART container / service instance. For ARK Code topic paths, `/v2/<service>/<asset_id>/events/<component>`, `asset_id` identifies the publishing instance, not the internal component. In a double-redundant deployment, two SS instances have distinct `asset_id` values while their `<component>` segments may both be `mission`, `ma`, etc.
- **MAID** — Unique MA ID.
- **TripId** — UINT16. Returns `65535` when no MA is authorized.
- **ServiceId** — String, references the 班次.
- **SS_ASSET_ID / SS_ID** — Safety Server instance ID, used in topic templates.
- **WSS_ID, TRIOPS_ID, MMS_ID** — Per-instance IDs used in topic templates.
