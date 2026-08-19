# ICD Topic Catalog (Types 1–19)

Complete topic map for tapas-icd v1.2.4 (latest as of skill creation). For payload schemas, fetch the corresponding page at http://10.2.10.51/icd/latest/ — this catalog is the index, not the spec.

## Topic Table

| # | Tag | Name | Topic | Freq | ACK | Notes |
|---|-----|------|-------|------|-----|-------|
| 1 | [ADS] | Vehicle System Info | `/v1/ads/system/<vehicle_id>` | On connect | No | ADS sysver + Ariel waypoint version. |
| 2 | [ADS] | Vehicle Status (車輛運行狀態) | `/v1/obs/status/<vehicle_id>` | 5Hz | No | Position, speed, op-mode, MA applied, **embeds `ArkCodeQueues`**. |
| 3 | [SS] | MA (車輛控制指令) | `/v1/ss/record/<SS_ASSET_ID>/3` (Mirror) | 2Hz | Yes | The Movement Authority pushed to a vehicle. **Field 17 `TSR`** = `List of TSR settings` — carries bulletin speed limits per zone. Full spec: http://10.2.10.51/icd/latest/type-03-ma |
| 4 | [ADS] | MA ACK | `/v1/ss/record/<SS_ASSET_ID>/4` (Mirror) | Per MA | Yes | Vehicle's response to MA. |
| 5 | [SS] | SS MA ACK | `/v1/ss/record/<SS_ASSET_ID>/5` (Mirror) | Per ACK | Yes | SS's confirmation of receiving the MA ACK. |
| 6 | [ADS] | ADS MA FIN ACK | `/v1/ss/record/<SS_ASSET_ID>/6` (Mirror) | Per MA finalize | Yes | Vehicle's finalize/completion acknowledgement. |
| 7 | [WSS] | WSS Status | `/v1/wss/status/<wss_id>` | 5Hz | No | Block / Signal / Door / Route / Operation / ABS Direction status. |
| 8 | [SS] | WSS Setting | `/v1/ss/setting/<ss_id>` | 1Hz | Yes | Setting commands SS pushes to WSS (e.g. IXLRouteSetting). |
| 9 | [WSS] | WSS Setting ACK | `/v1/ss/setting/<wss_id>` | Per Type 8 | No | Reply to Type 8. (Same topic root as Type 8.) |
| 10 | [WSS] | WSS System Info | `/v1/wss/system/<wss_id>` | On connect | No | IXL / WSS version info on connect. |
| 11 | [MMS] | VSI List ⚠️ | `/v1/mms/setting/<MMS_ID>` | 0.5Hz | No | **DEPRECATED** — use Type 17 instead. |
| 12 | [SS] | VSIES ⚠️ | `/v1/ss/status/<SS_ID>` | 0.5Hz | No | **DEPRECATED** — use Type 18 instead. |
| 13 | [TRI] | TriOps Setting | `/v1/triops/setting/<triops_id>` | 5Hz | No | Setting flow toward TriOps (publisher tagged [TRI] in ICD; verify direction in source if unclear). |
| 14 | [WSS] | TriOps Setting ACK | `/v1/triops/setting/<wss_id>` | Per Type 13 | No | WSS-side ack for TriOps setting. (Same topic root as Type 13.) |
| 15 | [SS] | System Hazard Status | `/v1/ss/system/<SS-ID>` | 1Hz | No | VSI status list — SS-side hazard reporting. |
| 16 | [SS] | System Severity Event | `/v2/ss/system-severity-event/<SS-ID>` | Event-based | No | v2 namespace. |
| 17 | [MMS] | VSI-v2 (Vehicle Service Instructions v2) | `/v2/mms/setting/2.900.01.0002` | Event-based | No | **Mirror of HTTP**: published when JPS→SS HTTP succeeds. Hardcoded ID in topic. |
| 18 | [SS] | VSIES-v2 (VSI Execution Status v2) | `/v2/ss/setting/mission/2.900.01.0001` | Event-based | No | **Mirror of HTTP**: published when SS→JPS HTTP succeeds. Hardcoded ID in topic. |
| 19 | [TRI] | TriOps Status (路側設備狀態) | `/v1/triops/status/<triops_id>` | 5Hz | No | **Embeds `ArkCodeQueues`** representing recent ARK Code activity. |

## Sub-message references

Several types contain sub-message structures referenced from other types:

- **Type 7 sub-sections:** `BlockStat`, `SignalStat`, `DoorStat`, `IXLRouteStat`, `OperationStat`, `ABSDirectionStat` — Type 3 MA references `DoorStat` from here.
- **Type 19 §[19-1]:** `ArkCodeQueue` — also referenced by Type 2.

## ARK Code in production

ARK Codes are **not** published on a separate `ark_code/...` topic in production. They are embedded as sub-fields:

- **Type 2 (Vehicle Status, ADS)** — field `ArkCodeQueues` (List of `ArkCodeQueue`), representing recent ADS-side ARK Code events.
- **Type 19 (TriOps Status)** — field `ArkCodeQueues` (List of `ArkCodeQueue`), representing recent TriOps-side ARK Code events.

The `QualifiedArkCodeId` format is `<source_tag>:<code_id_hex_string[2:]>`. Example:

```
/block_occupancy_health_monitoring/false_positive:03050103
```

The Cloud Team's separate ARK Code system with broker pattern `ark_code/<service>/<code_id_path>` and six categories (`error / warning / state / command / downgrade / audit`) is **still in backlog** and **not in production**.

For the full SS ARK Code design (hex format, MQTT topics, envelope schema, pending Confluence changes), see `references/ss-ark-code-design.md`.

**⚠️ Hex byte order correction:** Earlier drafts and session transcripts used `<DOMAIN><CATEGORY><COMPONENT><SEQ>`. The correct order is `<DOMAIN><COMPONENT><CATEGORY><SEQ>`. Do not copy from old sources.

## Naming pattern observations

- Most v1 topics: `/v1/<publisher>/<context>/<id>` — straightforward.
- v2 topics for VSI/VSIES (Types 17, 18): hardcoded IDs (`2.900.01.0001` / `2.900.01.0002`) instead of templated IDs.
- v2 topic for severity event (Type 16): `/v2/ss/system-severity-event/<SS-ID>` follows the v1-style pattern but in the v2 namespace.
- Mirror topics (Types 3, 4, 5, 6) all share the prefix `/v1/ss/record/<SS_ASSET_ID>/` with the type number as the final segment.
- A few topic roots are reused across send + ack pairs: Type 8 / Type 9 share `/v1/ss/setting/...`, Type 13 / Type 14 share `/v1/triops/setting/...`. Disambiguate by message direction and content.
- Vehicle Status uses `/v1/obs/status/...` (note `obs`, not `ads`) — this is a historical quirk worth noting when grepping.

## Update procedure

When the ICD changes:

1. Re-fetch http://10.2.10.51/icd/latest/ (Docusaurus sidebar lists all types).
2. Compare type list — add new entries, mark deprecated entries with ⚠️.
3. For each new or changed type, fetch the page header to grab `Topic`, `Frequency`, and `Ack Required` fields.
4. Update the table above and the *ARK Code in production* section if the ARK Code mechanism changes.
5. If a previously hardcoded topic ID changes (e.g. Types 17, 18), confirm with ICD source in Gerrit.
