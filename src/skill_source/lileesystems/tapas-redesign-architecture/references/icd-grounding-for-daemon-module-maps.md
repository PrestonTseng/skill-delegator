# ICD grounding for TAPAS daemon/module maps

Use this reference when updating TAPAS redesign daemon/module/data-schema diagrams from the live ICD.

## Lesson from 2026-07-13 daemon-module-map review

A user-provided ICD URL may be only the first page of a multi-page Docusaurus ICD. Do not infer the system schema from Type 1 alone. If the user names type numbers, navigate/read each requested type page and extract:

- message title,
- Type,
- Ack Required,
- Frequency,
- Topic or Mirror Topic,
- primary Message Format fields,
- linked sub-schema tables relevant to the architecture diagram.

For Camofox/browser review, start from the supplied ICD page and use either the sidebar/next links or direct known slugs. If browser JavaScript evaluation is blocked, the page snapshot still exposes the article tables; for bulk extraction, a plain HTML parser over the Docusaurus HTML can capture the same fields.

## Common ICD pages for daemon/module-map grounding

- Type 1 — Vehicle System Info
  - Topic: `/v1/ads/system/<vehicle_id>`
  - Use for ADS onboarding/system-version context.
  - Key fields: `ADSSysVersion`, `ArielVersion`.

- Type 2 — Vehicle Status
  - Topic: `/v1/obs/status/<vehicle_id>`
  - Frequency: `5Hz`
  - Use for SS Train Tracking / ADS telemetry.
  - Key fields include: `Milepost`, `BlockId`, `LaneId`, `Direction`, `GeoLat`, `GeoLng`, `Speed`, `OperationMode`, `SystemHealthy`, `DoorCtrlStatus`, `AppliedMAId`, `VehicleId`, `ServiceId`, `BatteryLevel`, `VehicleStatus`, `AreaOutOfService`, `TripId`, `ArkCodeQueues`, `DOM`, `MissionInfo`, `AdsVersion`.
  - Sub-schemas to check: Mission Info, Ark Code Queue, Ark Code Snapshot, DOM.

- Type 3 — MA
  - Mirror Topic: `/v1/ss/record/<SS_ASSET_ID>/3`
  - Frequency: `2Hz`
  - Ack Required: `Yes`
  - Use for SS Movement Authority Manager and TSR projection.
  - Key fields include: `MAID`, `VehicleId`, `ServiceId`, `StartTime`, `EndTime`, `TripId`, `RouteList`, `AuthorizedDir`, `OperationMode`, `AuthorizedSpeed`, `FacingSigId`, `FacingSigStat`, `NextFacingSigId`, `NextFacingSigStat`, `VehicleDoorCtrl`, `ArielDigest`, `TSR`, `PlatformDoorStat`, `StartMp`, `EndMp`, `DepartureTime`, `DepartureSignal`, `DOM`, `VehicleStatusReference`, `WSSStatusReference`, `MissionQueue`, `MissionUuid`, `MissionStaticId`, `SafetyServerVersion`.
  - TSR sub-schema fields: `FromMP`, `ToMP`, `LaneId`, `SpeedLimit`, `Mode`, `StartTime`, `EndTime`, `TSRId`, `BrakingCurveNum`.

- Type 7 — WSS Status
  - Topic: `/v1/wss/status/<wss_id>`
  - Frequency: `5Hz`
  - Use for WSS Infrastructure State, Signal/wayside indicator, and route-status display.
  - Primary fields: `BlockStat`, `SignalStat`, `PlatformDoorStat`, `RouteStat`, `OperationStat`, `AbsDirectionStat`.
  - Sub-schemas to check: Block occupancy/authorized status, Signal status, Door status, IXLRouteStat, OperationStat, ABS direction.

- Type 8 — WSS Setting
  - Topic: `/v1/ss/setting/<ss_id>`
  - Frequency: `1Hz`
  - Ack Required: `Yes`
  - Use for SS/WSS route and platform-door commands.
  - Primary fields: `IXLRouteSetting`, `PlatformDoorSetting`.
  - Door setting fields: `Name`, `Value`, `OpenInterval`.

- Type 13 — TriOps Setting
  - Topic: `/v1/triops/setting/<triops_id>`
  - Frequency: `5Hz`
  - Use for TriOps block occupancy input to WSS/infrastructure state.
  - Primary field: `BlockStat`.
  - BlockStat fields: `Name`, `Occupancy`; ICD note says if TriOps cannot provide valid occupancy state, it marks the block as occupied.

- Type 17 — VSI-v2
  - Topic: `/v2/mms/setting/2.900.01.0002`
  - Frequency: `Event Based`
  - Use for JPS/MMS/SS mission-list scheduling context.
  - Primary field: `Mission List`.
  - Mission fields: `id`, `date`, `service_id`, `mission_id`, `ads_id`, `trip_id`, `start_time`, `depart_time`, `arrive_time`, `end_time`, `state`.
  - State values include `SCHEDULED`, `LOCKED`, `ACTIVE`, `COMPLETED`, `CANCELED`.

- Type 18 — VSIES-v2
  - Topic: `/v2/ss/setting/mission/2.900.01.0001`
  - Frequency: `Event Based`
  - Use for SS → JPS mission execution status / progress-state grounding.
  - Fields: `service_id`, `mission_uuid`, `mission_static_id`, `action`.
  - Action values: `update`, `lock`, `cancel`, `start`, `complete`.

## Diagram-writing pitfall

For the first overview diagram requested as “daemon → module → responsibility → data schema,” keep it hierarchy-only. Do not add runtime arrows between daemons in that diagram; put runtime flow into later sequence diagrams. When grounding schemas in ICD, name the ICD type/topic inline inside each schema node so reviewers can distinguish live ICD payload fields from proposed logical schema fields.
