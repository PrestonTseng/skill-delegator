# SS ARK Code Design — Decisions & Rationale

Authoritative record of design decisions for the Safety Server ARK Code system (Cloud Team).
Confluence draft lives at page `3732963434` (Backlog — Safety Server ARK Code Design).
Status: **backlog / not in production** as of May 2026.

---

## Hex CodeId Format

**Correct byte order:** `<DOMAIN><COMPONENT><CATEGORY><SEQ>`

| Byte | Name | Values |
|------|------|--------|
| 1 | **Domain** | `01` = Safety Server |
| 2 | **Component** | `01`=MissionExecutor/Nibble, `02`=WssAgentService, `03`=MAManagerService, `04`=VehicleStatusTracker, `05`=SeverityEventHandler, `06–09` reserved, `0A`=System |
| 3 | **Category** | `01`=state, `02`=command, `03`=warning, `04`=error, `05`=downgrade, `06`=audit |
| 4 | **Sequence** | Per-component, starting at `01`, no semantic meaning |

Example: `01 01 03 05` = Domain:SS / Component:MissionExecutor / Category:warning / SEQ:5

**Reading order rationale:** DOMAIN→COMPONENT→CATEGORY→SEQ follows "locate position first, then classify" — a more natural decomposition than the earlier draft's DOMAIN→CATEGORY→COMPONENT→SEQ.

**⚠️ Common mistake:** Earlier drafts and session transcripts used `<DOMAIN><CATEGORY><COMPONENT><SEQ>`. That order is **wrong** — do not copy from those sources.

---

## Why DOMAIN byte is kept (even though topics are SS-only)

`CodeId` is designed to be self-contained outside MQTT context. When codes appear in logs, databases, or alerting systems, the MQTT topic is gone. The DOMAIN byte is the only thing preventing `01 01 03 05` (SS) from colliding with a future `02 01 03 05` (MMS) in shared infrastructure.

DOMAIN's justification is **CodeId persistence and global uniqueness**, not topic structure.

---

## MQTT Topic Structure

Six dedicated topics per SS instance:

```
/v2/ss/<SS_ASSET_ID>/events/mission
/v2/ss/<SS_ASSET_ID>/events/wss
/v2/ss/<SS_ASSET_ID>/events/ma
/v2/ss/<SS_ASSET_ID>/events/obs
/v2/ss/<SS_ASSET_ID>/events/severity
/v2/ss/<SS_ASSET_ID>/events/system
```

Note: `obs` (not `vehicle`) for consistency with ICD Type 2 `/v1/obs/status/`.

---

## Future Service Expansion (MMS / JPS / WSS)

Design principle: **each service owns its own topic namespace**. Never merge multiple publishers onto one topic.

Convention for future services:
```
/v2/<service>/<asset_id>/events/<component>
```

`asset_id` is the unique identifier of the publishing container/instance, not the internal component name. In double-redundant deployments, each redundant service instance has its own distinct `asset_id`; components are represented by the final `<component>` topic segment.

A client subscribing to all services uses wildcard: `/v2/+/+/events/#`

This satisfies "single subscription for all events" without collapsing publisher boundaries.

---

## Envelope Schema

Every message on every `events/` topic:

```json
{
  "Timestamp": 1720000000000,
  "SsId": "2.900.01.0001",
  "CodeId": "01010305",
  "QualifiedArkCodeId": "/ss/mission/departure_block_exit_timeout",
  "Category": "warning",
  "PayloadType": "MissionPayload",
  "Payload": { ... }
}
```

- `CodeId` = 8 hex chars (machine use: switch/lookup)
- `QualifiedArkCodeId` = human-readable primary key, format `/ss/<component>/<event_name>`

---

## Pending Confluence Updates (page 3732963434)

When updating the Confluence page, apply ALL of the following:

- [ ] A. Fix byte order definition: DOMAIN-CATEGORY-COMPONENT-SEQ → **DOMAIN-COMPONENT-CATEGORY-SEQ**
- [ ] B. Recalculate ALL example CodeIds (bytes 2 and 3 were swapped in old drafts)
- [ ] C. Add DOMAIN byte rationale (CodeId persistence / global uniqueness)
- [ ] D. Add MQTT topic future expansion section (each service owns namespace + wildcard pattern)
- [ ] E. Add `06–09 reserved` note in Component byte table
