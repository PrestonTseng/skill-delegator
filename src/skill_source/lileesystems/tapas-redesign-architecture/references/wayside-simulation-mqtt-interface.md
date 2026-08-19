# Wayside simulator MQTT and runtime interface design

Use this reference when defining or reviewing component state, commands, MQTT topics, or simulator/console boundaries for WSS/OpenPLC/plcsim.

## Source-first workflow

1. Fetch the current `devops/tapas-icd` master and read the live WSS Status, WSS Setting, WSS Setting ACK, and WSS System Info pages. Do not copy topic/payload details from this reference as if they were current authority.
2. Read the current plcsim canonical YAML schemas and the accepted route-command/asset-state ADR.
3. Separate four layers before proposing topics:
   - static configuration/topology;
   - command intent;
   - physical observed feedback and health/freshness;
   - derived interlocking/route state.
4. Reuse existing aggregate ICD topics unless an external consumer actually requires a new contract. Do not create one MQTT topic per component by default.
5. Record unresolved scope decisions explicitly, especially PlatformDoor coverage and whether raw switch/detection proof must be externally visible.

## Domain boundary

### Static configuration, not writable runtime components

- Site/domain enums
- Vertex
- Sub-block
- Route definition/topology

Deliver these through a versioned generated configuration artifact. Do not make them mutable MQTT state.

### Operational resources

- **Signal:** commanded aspect, independently observed aspect, health/freshness, governing route. Normal dispatch does not directly command a proceed aspect.
- **Switch/point machine:** commanded position, observed position, correspondence, and health/freshness. Normal dispatch does not command individual switches. Do not store a second writable `lock_owner` on switch status; derive route lock ownership from active Route state.
- **Detection section:** occupancy, health, freshness. No normal command; test injection is privileged and isolated.
- **Block:** derived occupancy/authorization/quality/lock owner. Never create a second writable block-occupancy truth beside detector feedback.
- **ABS direction:** requested/effective direction and health/freshness as a derived corridor aggregate. Prefer route-owned direction control. Do not expose a generic public direction-write command until the territory authority, proving, transition, and cancellation workflow is explicitly approved; following trains use occupancy-triggered block routes without repeated per-train route requests.
- **Route/interlocking resource:** lifecycle, blockers, request ID, no-entry deadline, release state, and failure reason. Lock/resource ownership is derived from active Route state rather than duplicated on switches/blocks. Normal commands are request and cancel; route eligibility check is a side-effect-free advisory query.
- **WSS/controller:** startup/recovery/operational state, control mode, health/hazards, version and config revision. Reset/recover is privileged.
- **PlatformDoor:** include it in the complete target domain model when it is a known WSS asset, but decide separately whether the first simulator increment implements it. Model normal operation as an independently authorized station workflow (`open|close|reset|keep_open`) with separate internal field output and observed-state proof. Route setting must never open or close doors implicitly.

## Minimum external MQTT shape

Prefer the existing WSS command/ACK/status/system topic families defined by the live ICD rather than per-asset topics:

- SS to WSS setting command;
- WSS to SS correlated setting ACK;
- WSS full status snapshot;
- WSS system/version info.

A full periodic WSS status snapshot normally removes the need for a separate MQTT snapshot-request topic. If external SS does not consume raw switch/detection proving details, keep them in the simulator/backend runtime interface rather than extending MQTT.

## Critical semantics

- **ACK is not completion.** The command ACK says received/accepted/rejected. Independently observed state proves that the requested condition was achieved.
- **Commanded state is not observed state.** A PLC command variable cannot prove its own success.
- **Route query is not authority.** `check_route` is advisory; `request_route` revalidates while acquiring interlocking resources.
- **Retries need idempotency.** Carry a stable command/request ID across retries; broker QoS is not a substitute.
- **Commands are never retained.** Define QoS/retain explicitly in the ICD. State may be retained only when consumers enforce timestamps, freshness, and recovery inhibit.
- **Simulation injection is not production control.** Isolate occupancy/health/fault injection behind a privileged API or namespace.
- **Browser ownership:** the dispatch browser calls its backend; it does not connect directly to MQTT or OpenPLC.

## Minimum canonical interfaces

- `StaticDefinition`: versioned config/topology/assets/routes/enums/timing plus config hash.
- `WaysideStateSnapshot`: schema version, site/WSS ID, config revision, source, timestamp, monotonic sequence, controller state, and per-component observed state with health/freshness.
- `RouteCommand`: stable command ID, route ID, REQUEST/CANCEL action, issued time, source, optional deadline.
- `CommandResult`: command ID, target reference, phase (`RECEIVED/ACCEPTED/REJECTED/COMPLETED/FAILED/TIMED_OUT`), reason, and timestamp. `ACCEPTED` proves admission only; `COMPLETED` requires independent observed feedback, and the continuing state snapshot remains the authority for achieved state.
- `CheckRoute`: side-effect-free eligibility and structured blockers, preferably HTTP/backend query.
- `SimulationInjection`: privileged test-only state/fault injection.

## Review questions

Before accepting the interface, obtain explicit decisions on:

1. Is normal dispatch route-only except for separately authorized station workflows such as PlatformDoor operation?
2. Is ABS direction fully route-owned, and if not, what exact authority/proving/cancellation workflow permits direction-family changes?
3. Are platform doors implemented in this simulator increment, even though they remain in the complete target domain model?
4. Does an external consumer need raw switch/detection/proving detail?
5. Does the external contract need explicit completed/failed command events, or are ACK plus observed status sufficient?
6. What exact QoS and retain policy applies to every topic?
