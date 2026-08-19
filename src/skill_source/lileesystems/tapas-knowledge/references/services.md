# TAPAS Service Catalog

Each entry: owner team, purpose, key responsibilities, and which other services it talks to. Topic schemas live in **tapas-icd** (see `icd-topics.md` for the full topic table).

Quick ownership map:

| Team | Services |
|------|----------|
| **Cloud Team** | Safety Server (SS), MMS, JPS, Seshat, Faramund, WSS, Hydra, OpenPLC |
| **ACES Team** | ADS, TriOps, ARK Code System (the original design) |

> **Ownership history note:** WSS and OpenPLC originally belonged to the **LileeOS** team and have transitioned to Cloud Team. When reading older docs that say "LileeOS owns WSS" or "LileeOS owns OpenPLC", treat that as outdated.

---

## Cloud Team Services

### Safety Server (SS)

- **Owner:** Cloud Team. Preston is the primary technical owner.
- **Codename:** Thalos. Source repo: `/workspace/thalos` (Python / FastAPI / asyncio).
- **Purpose:** Orchestrate vehicles to execute missions safely. Sit between JPS, WSS, and ADS as the safety-critical coordinator.
- **Architecture:** Two-tier.
  - **Core Services** (WSS Agent, WSS Registration, ADS Agent, JPS Agent, MA Manager) handle external integrations.
  - **Mission Execution** (Mission Executor + Nibble Executor FSMs) runs the schedule.
- **Stateful:** New SS is stateful (refactored from the previous stateless version). Execution is observable via the Safety Server Grafana Dashboard, which also exposes WSS-as-seen-by-SS and ADS-as-seen-by-SS.
- **Config:** Pydantic `Settings` (loaded from `.env`). Key knobs: `asset_id`, `ma_frequency_ms` (500ms), `ma_validity_ms` (9s), `ma_limit_range` (2 blocks), `mission_lock_offset_ms` (-5min), `mission_exec_offset_ms` (-2min), `departure_timeout_ms` (5min), `await_nibble_entry_timeout_ms` (5min). Feature flags: `mock_ads_enabled`, `mock_triops_enabled`, `ads_command_mqtt_mirror`, `vsi_mqtt_mirror`, `severity_event_mqtt_mirror`.
- **Dependency injection:** `ServiceRegistry` (IoC container) in `core/dependency_manager.py`. All services wired via interface → implementation registration.
- **MA Manager:** Auto-creates an MA when a vehicle connects, dispatches MA at 500ms heartbeat, resets mission fields on ADS reconnect (preserves DOM/TSR), auto-clears on disconnect.
- **MissionExecutor FSM states (happy path):** `INITIALIZING → LOCKING → LOCKED → ADS_ALLOCATING → ADS_ALLOCATED → AWAIT_ACTIVATE → ACTIVATING → ACTIVATED → DOOR_OPENING → DOOR_OPENED → AWAIT_DEPARTURE → DOOR_CLOSING → DOOR_CLOSED → ROUTE_REQUESTING → ROUTE_AUTHORIZED → DEPARTING → DEPARTED → NIBBLE_EXECUTING → ARRIVING → FINALIZING → COMPLETED`. Error states: `LOCK_ERROR`, `ADS_ALLOCATE_ERROR`, `ACTIVATE_ERROR`, `DOOR_OPEN_ERROR`, `DOOR_CLOSE_ERROR`, `ROUTE_REQUEST_ERROR`, `DEPART_ERROR`, `NIBBLE_EXECUTE_ERROR`, `FINALIZE_ERROR`. Terminal states: `COMPLETED`, `TERMINATED`, `CANCELED`.
- **NibbleExecutor FSM states:** `INITIALIZING → AWAIT_BLOCK_ENTRY → BLOCK_ENTERED → ROUTE_REQUESTING → ROUTE_AUTHORIZED → MA_REFRESHING → MA_REFRESHED → FINALIZING → COMPLETED`. Error states: `AWAIT_BLOCK_ENTRY_TIMEOUT_ERROR`, `ROUTE_REQUEST_ERROR`, `MA_REFRESH_ERROR`, `FINALIZE_ERROR`. Terminal: `COMPLETED`, `TERMINATED`.
- **SeverityEventHandler** maps external events to DOM: `MINOR_EARTHQUAKE → DOM_7`, `MAJOR_EARTHQUAKE → DOM_9`, `HEAVY_RAIN → DOM_2`. Applied to all connected ADS vehicles via `MaManagerService.set_dom()`.
- **VehicleStatusTracker:** Per-vehicle observable holder. Stores `current` + `previous` VehicleStatus, notifies change listeners. Used by NibbleExecutor (block entry detection) and MissionExecutor (departure block exit, PARKED detection).
- **Mock services:** `MockAdsService` (simulates ADS vehicles over WebSocket + MQTT) and `MockTriOpsService` (simulates block occupancy via TriopsSetting at 200ms). Both enabled by feature flags.
- **Talks to:**
  - **WSS** — route authorization (Type 8 setting / Type 9 ack), block / signal / route state (Type 7).
  - **ADS** — MA push (Type 3), receives MA ACK (Type 4), publishes SS MA ACK (Type 5), receives MA FIN ACK (Type 6).
  - **JPS** — schedule sync via HTTP, mission status via HTTP; both mirrored on MQTT (Type 17 VSI-v2 inbound, Type 18 VSIES-v2 outbound).
  - **MMS** — REST API (Route Board, manual operations) plus status feeds.
- **Publishes:** Type 3 MA, Type 5 SS MA ACK, Type 8 WSS Setting, Type 12 VSIES (deprecated) / Type 18 VSIES-v2, Type 15 System Hazard Status, Type 16 System Severity Event.

### MMS (Management and Monitoring Server)

- **Owner:** Cloud Team.
- **Purpose:** Real-time visualization and control interface for the OCC. The operator's primary touchpoint.
- **Key features:** Vehicle management page, M5 Table (mission display), Manual Mode controls, TSR creation / approval workflow, Delay prediction display, Logs visualization, ARK Code display per vehicle, Service Health Dashboard (planned).
- **Architectural note:** MMS is the **aggregation layer for OCC** — OCC frontends do NOT subscribe to MQTT directly. Roadmap: evolve into an independent **OCC Console** that consumes both JPS and MMS APIs.
- **Talks to:**
  - **SS** — REST API for control actions, status feeds for OCC display.
  - **JPS** — schedule editing UI.
  - **MQTT broker** — consumes ARK Code stream (embedded in Type 2 vehicle status and Type 19 TriOps status) for OCC display.
- **Publishes:** Type 11 VSI (deprecated) / Type 17 VSI-v2.

### JPS (Journey Planning System)

- **Owner:** Cloud Team.
- **Also expanded as:** Journal Planning System (used interchangeably in some docs).
- **Purpose:** Generate train schedules from capacity requirements. Detect potential conflicts between trips. Support real-time schedule adjustment.
- **Notable:** Algorithmic core — schedule generation and conflict detection are non-trivial. Source of truth for *what missions to run*.
- **Talks to:**
  - **SS** — provides schedules (HTTP, mirrored on Type 17 VSI-v2), receives mission execution status (HTTP, mirrored on Type 18 VSIES-v2).
  - **MMS** — UI for schedule editing.

### Seshat (Seshat-Go)

- **Owner:** Cloud Team.
- **Purpose:** End-to-end monitoring and replay platform. Subscribes the entire MQTT broker, persists to TimescaleDB, exposes a query API and a track-map visualization.
- **Stack:** Go, Clean Architecture, paho.mqtt.golang + pgx/v5 + chi.
- **Use case:** Engineering tool — post-mortem analysis, QA debugging, ARK Code historical query.
- **Explicitly not a product dependency:** MMS / monitoring do not depend on Seshat uptime.

### Faramund

- **Owner:** Cloud Team.
- **Purpose:** Automated dispatcher agent. Two responsibilities:
  1. **DOM 10 vehicle recovery** — coordinates with MMS / JPS / SS and the Felicia dispatcher to pull a broken-down vehicle back to yard. Implemented as a 28-state FSM.
  2. **WSS Anomaly Detection** — workaround layer detecting WSS misbehavior (route timeout, block-occupancy mismatch, mission-completion anomalies). Currently the mitigation layer for SART-1631 / 1658 / 1659 family defects.
- **Protocol:** Faramund ↔ Felicia over WebSocket using message types D0–D4 (down) and U0–U7 (up).

### Hydra

- **Owner:** Cloud Team.
- **Purpose:** Headless recording agent. Spins up Chrome instances and records:
  - **M1–M3** — real-time schedule pages.
  - **M5** — real-time schedule (the M5 Table).
  - **M6.c** — vehicle management.
- **Codebase:** https://lilee-ci-tw.lileesystems.com/gerrit/plugins/gitiles/tcloud/safeart/hydra/+/refs/heads/master
- **Use case:** Capturing OCC-side UI state for post-incident review and QA.

### WSS (Wayside Safety Server)

- **Owner:** Cloud Team. (Transitioned from LileeOS — note this when reading older docs.)
- **Purpose:** Trackside safety controller. Authorizes routes, tracks block occupancy, interfaces with the trackside PLC layer.
- **Talks to:**
  - **SS** — receives `WSS Setting` commands (Type 8), responds with `WSS Setting ACK` (Type 9), publishes `WSS Status` (Type 7) and `WSS System Info` (Type 10), publishes `TriOps Setting ACK` (Type 14).
  - **TriOps** — receives upstream block-occupancy state.
- **Known stable issue class:** Block occupancy sync delays after prolonged uptime cause "stuck green" blocks. Mitigated by Faramund WSS Anomaly Detection pending a long-term fix to the WSS ↔ TriOps sync mechanism.

### OpenPLC

- **Owner:** Cloud Team. (Transitioned from LileeOS.)
- **Purpose:** PLC-side software for trackside signal control.
- **Critical operational fact:** When OpenPLC fails, signals misbehave and block-entry requests fail — the **symptoms surface downstream** on the signaling and block-entry flow. WSS is commonly suspected first; the actual root cause is OpenPLC. This pattern motivates the planned MMS Service Health Dashboard.

---

## ACES Team Services

### ADS (Autonomous Driving System)

- **Owner:** ACES Team.
- **Purpose:** Vehicle-side autonomous driving software. Receives MA from SS, executes movement, reports position / DOM / status.
- **Talks to:** SS via SS's ADS Agent — receives Type 3 MA, sends Type 4 MA ACK / Type 6 MA FIN ACK, continuously publishes Type 1 Vehicle System Info (on connect) and Type 2 Vehicle Status (5Hz, includes embedded `ArkCodeQueues`).
- **Identifiers:** Vehicle IDs follow the `ADS-XXXX` pattern (e.g. `ADS-0001`). VehicleId == AssetId.
- **Reports:** position (milepost / block / lane / sub-block / lat-lng), speed, operation mode, system healthy bitmask, applied MA ID, charging / battery state, vehicle running status.

### TriOps

- **Owner:** ACES Team.
- **Purpose:** Trackside operations controller. Reports block occupancy and other trackside state upstream.
- **Talks to:** WSS — receives Type 13 TriOps Setting, publishes Type 19 TriOps Status (5Hz, includes embedded `ArkCodeQueues`).

### ARK Code System (cross-cutting)

- **Origin:** ACES Team's design.
- **Purpose:** Real-time coded event stream for monitoring TriOps and ADS state. Used when integrating with TriOps and ADS.
- **In production:** ARK Codes are **embedded sub-fields** inside Type 2 (Vehicle Status, ADS) and Type 19 (TriOps Status) — *not* a separate MQTT topic.
- **`QualifiedArkCodeId` format:** `<source_tag>:<code_id_hex_string[2:]>`. Example: `/block_occupancy_health_monitoring/false_positive:03050103`.
- **Schema authority:** ICD Type 19 §[19-1] and Type 2 §`ArkCodeQueue`.
- **Cloud Team's parallel system** (still in backlog, not implemented): proposed broker pattern `ark_code/<service>/<code_id_path>` with six categories — `error / warning / state / command / downgrade / audit` — for SS / SE / JPS / MMS internal events. **Do not reference this as live infrastructure**; it is a future plan.
- **Consumers:** Seshat (full subscription, archival), MMS (filtered, OCC display), third-party monitoring (independent subscription).
