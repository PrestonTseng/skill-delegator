# TAPAS Communication Patterns

How TAPAS services exchange data, where the source of truth lives, and how environments are organized.

## MQTT Broker

The MQTT broker is the spine of TAPAS. Most async cross-service events flow through it. Topic schemas, QoS, payload formats — all defined in **tapas-icd**. A handful of inter-service interactions still use HTTP (JPS ↔ SS schedule sync, MMS ↔ SS control actions); those flows are **mirrored** onto MQTT via the v2 message types so that downstream consumers can read everything from one place.

### Topic naming convention

The general pattern is:

```
/v<api-version>/<publisher>/<context>/<id>
```

Examples:

- `/v1/wss/status/<wss_id>` — WSS publishes status
- `/v1/triops/status/<triops_id>` — TriOps publishes status
- `/v1/ads/system/<vehicle_id>` — ADS publishes system info
- `/v1/obs/status/<vehicle_id>` — ADS publishes vehicle status (note: prefix is `obs` not `ads` for vehicle status — historical quirk)
- `/v1/ss/setting/<ss_id>` — SS publishes WSS setting commands
- `/v2/ss/system-severity-event/<SS-ID>` — SS publishes severity events (v2 namespace)
- `/v2/mms/setting/2.900.01.0002` — MMS publishes VSI-v2 (note: hardcoded ID, not templated)
- `/v2/ss/setting/mission/2.900.01.0001` — SS publishes VSIES-v2

### Mirror Topics

Some types declare a **Mirror Topic** rather than a regular `Topic`:

```
/v1/ss/record/<SS_ASSET_ID>/<type-number>
```

This is the broker-wide archival copy of a message that's primarily delivered through another channel (direct or RPC). Mirror topics exist so Seshat and other observers can capture the full message stream without intercepting the primary delivery path.

Types using the Mirror Topic pattern: 3 (MA), 4 (MA ACK), 5 (SS MA ACK), 6 (ADS MA FIN ACK).

## tapas-icd — the source of truth

- **Rendered website:** http://10.2.10.51/icd/latest/ (Docusaurus site)
- **Source code (Gerrit):** https://lilee-ci-tw.lileesystems.com/gerrit/plugins/gitiles/devops/tapas-icd/+/refs/heads/master
- **Authority:** ICD is the **single source of truth** for topic names, payloads, frequencies, and ACK requirements. When in doubt, fetch from ICD — do not guess from this skill or from memory.
- **Versioning:** tapas-icd has its own version-bump process. The Introduction page on the site documents the current flow; the process was redefined in 2026-03 to clarify ownership and approval.
- **Other docs hosted at the same site:**
  - `/deployment/latest/` — Deployment docs
  - `/thalos/latest/` — Safety Server (Thalos) internal docs (e.g. mission_error_recovery)
- **Available ICD versions:** 1.2.4 (latest), 1.1.3, 1.0.2, 0.1.

## Inter-service Interactions (high-level map)

For exact topic names and frequencies, see `icd-topics.md`.

### MA flow (SS ↔ ADS)

```
SS  ── Type 3 MA ──────────────▶ ADS
SS  ◀── Type 4 MA ACK ───────── ADS
SS  ── Type 5 SS MA ACK ──────▶ (mirror; confirms SS received the ACK)
SS  ◀── Type 6 ADS MA FIN ACK ─ ADS  (vehicle finished the MA)
```

All four types use the Mirror Topic pattern (`/v1/ss/record/<SS_ASSET_ID>/N`) for broker-wide visibility.

### Route / Block authorization (SS ↔ WSS ↔ TriOps)

```
SS     ── Type 8 WSS Setting ──────▶ WSS
SS     ◀── Type 9 WSS Setting ACK ── WSS
WSS    ── Type 7 WSS Status ───────▶ (broker; SS subscribes for block / signal / route state)
WSS    ── Type 10 WSS System Info ▶ (on connect)

WSS    ── Type 13 TriOps Setting ──▶ TriOps   (note: ICD tags this [TRI] but flow is from WSS)
WSS    ── Type 14 TriOps Setting ACK ▶ (broker)
TriOps ── Type 19 TriOps Status ───▶ (broker; includes ARK Code Queue)
```

The TriOps → WSS occupancy update path is the upstream of the SART-1631 stuck-green-block chain.

### Schedule flow (JPS ↔ SS ↔ MMS)

Primary path is HTTP. The MQTT v2 messages mirror the HTTP delivery for downstream consumers.

```
JPS  ── HTTP ──▶  SS     (schedule push; Type 17 VSI-v2 is mirrored on MQTT when JPS→SS HTTP succeeds)
SS   ── HTTP ──▶  JPS    (mission status; Type 18 VSIES-v2 is mirrored on MQTT when SS→JPS HTTP succeeds)
MMS  ◀── REST API ──▶ SS  (control actions, status feeds)
MMS  ── UI ──▶ JPS       (schedule editing)
```

### ADS reporting (ADS → MQTT broker)

```
ADS ── Type 1 Vehicle System Info ──▶ /v1/ads/system/<vehicle_id>     (on connect)
ADS ── Type 2 Vehicle Status ───────▶ /v1/obs/status/<vehicle_id>     (5Hz, includes ArkCodeQueues)
```

### SS-side system events

```
SS ── Type 15 System Hazard Status ───────▶ /v1/ss/system/<SS-ID>                     (1Hz)
SS ── Type 16 System Severity Event ──────▶ /v2/ss/system-severity-event/<SS-ID>      (event-based)
```

### Recording / archival

- **Seshat** subscribes broker-wide for archival. No direct topic dependency from other services.
- **Hydra** records UI state (Chrome-driven) for M1–M3 / M5 schedule pages and M6.c vehicle management. Does not depend on MQTT.

### OCC / frontend

- **MMS → OCC frontend** — WebSocket / REST. OCC does **not** subscribe to MQTT directly.

### DOM 10 recovery

- **Faramund ↔ Felicia** — WebSocket protocol with D0–D4 (down) and U0–U7 (up) message types.
- **Faramund ↔ MMS / JPS / SS** — alert ingestion (DOM 10 alerts), Manual Mode activation, mission cancellation, route authorization on the recovery path.

## Environments

### Alpha (the live shared testbed)

- **Authoritative reference:** https://lileesystems.atlassian.net/wiki/spaces/TAPAS/pages/2731540565/Alpha
- All deployment topology, credentials, and access patterns live there.

### Pre-Alpha (now means "team-local testbed")

The name has shifted. "Pre-Alpha" no longer refers to a single shared environment; it refers to the **tapas-testbed** project — each team checks it out and builds their own testbed locally.

- **Repo:** https://lilee-ci-tw.lileesystems.com/gerrit/admin/repos/tcloud/test/tapas-testbed,general
- **README:** https://lilee-ci-tw.lileesystems.com/gerrit/plugins/gitiles/tcloud/test/tapas-testbed/+/refs/heads/master/README.md
- **Implication:** When a teammate says "Pre-Alpha", confirm whether they mean the legacy shared environment (rare, retired) or "my local tapas-testbed".

### Production

Deployed customer sites. Specifics confidential / out of scope for this skill.

## Cross-team Conventions

- **ICD ownership** — ACES Team historically owned ICD content; the version-bump process was redefined in 2026-03. Check the ICD Introduction page for current procedure.
- **Cross-team coordination** — Tapas Meeting (recurring sync). Each team maintains a Known Issues List (KIL) with `Description / Confluence link / Status / Impact / Mitigation / Long-term Solution` columns.
- **Release notes** — Cloud Team uses the `release-commit-summary` skill to generate cross-team release commit summaries from the H1 KPI page.
- **Tickets** — Use the `jira-ticket-writer` skill for SART-board ticketing conventions (Task / Story / Bug structures).
