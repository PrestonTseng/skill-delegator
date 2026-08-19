---
name: railway-infrastructure-tooling
description: Research, compare, and select graphical/editor tooling and exchange formats for railway infrastructure, topology, simulation, railML/RTM, GIS, and interlocking-route definitions.
---

# Railway Infrastructure Tooling

## Use this skill when

- comparing railway infrastructure editors, viewers, converters, or simulators;
- evaluating OSRD, OSM/OpenRailwayMap/JOSM, SUMO, railML, RailTopoModel, or similar tooling;
- choosing a source-of-truth format for track topology or signaling data;
- assessing whether a tool models genuine interlocking routes rather than geographic or simulation routes.

## Research workflow

1. **Set the required semantic level.** Clarify whether the need is geographic assets, physical topology, simulation, timetable paths, signaling behavior, or interlocking application data.
2. **Use primary sources only when requested.** Prefer official documentation, the maintained source repository, schema/model source, license file, and official format registry. Treat project READMEs as claims to verify against serialization code.
3. **Separate authoring from viewing.** A renderer or validator is not an editor. An import path does not prove round-trip export.
4. **Inspect the native model.** Record editable object classes, persistence format, namespaces, and supported import/export directions.
5. **Separate licenses.** Check editor code, map/database content, exchange schema, examples, and documentation independently.
6. **Test the meaning of “route.”** Distinguish geographic railway-line relations, train itineraries, simulator vehicle routes, RINF vehicle/infrastructure Route Compatibility Checks, signaling blocks, and signal-to-signal interlocking routes. An interlocking control-area relation is also not an interlocking route table.
7. **Audit interlocking completeness.** Look specifically for entry/exit, permitted port transitions, required point positions, release sections, route conflicts, overlap, flank protection, and locking/release rules. Equipment presence, logical grouping, or network connectivity alone is insufficient evidence.
8. **Report negative findings narrowly.** Say that a cited schema lacks an explicit field or that current official docs do not establish a capability; do not claim universal impossibility.
9. **Separate exchange fitness from SSOT fitness.** Evaluate semantic coverage, maintenance/governance, authoring and transaction needs, stable-ID/version rules, extension policy, validation, migrations, and legal constraints independently. A rich XML/XSD exchange schema is not automatically a good mutable application database.
10. **Resolve “open” through operative terms.** Record registration, certification, commercial-use, derivative-work, and redistribution conditions; do not equate an official “open-source/open-data” description with a permissive or OSI-style license.
11. **Separate static exchange semantics from runtime control.** When applying railML to a simulator, PLC, HMI, or MQTT/API contract, use railML IDs/classes/relationships for static infrastructure and interlocking engineering data. Put timestamps, health, freshness, commanded-vs-observed state, correlation/idempotency, ACK/result phases, QoS/retain, and simulation injection in a separate application runtime layer that references stable static IDs. Do not call internal JSON/YAML “railML XML” or “certified railML.”
12. **Build a deterministic crosswalk before migration.** Map every source ID/field to a railML element/property, an explicit application extension where no exact match exists, and any legacy interface projection. Preserve unresolved engineering data as explicit blanks rather than inferred facts.
13. **Present a concise evidence table.** Include tool role, authoring/export, serialization, license, maturity/maintenance, route semantics, SSOT suitability, decisive limitation, and exact primary-source URLs.

## Core decision rule

Never infer interlocking semantics merely because a tool can draw tracks, switches, signals, or “routes.” A railway SSOT may need separate but linked layers for geospatial assets, physical track transitions, and operational/interlocking rules.

## Verification pitfalls

- Do not conflate OpenRailwayMap with an editor; it is principally an OSM-based renderer and tagging ecosystem.
- Do not equate `route=railway` or a simulator vehicle route with a signal-to-signal locking route.
- Do not call software open source based only on “freeware,” downloadable source, or an “open” schema name; inspect the actual license terms.
- For railML tools, verify certification and whether custom namespaces carry the claimed route/interlocking fields.
- Prefer current schema/model source over marketing summaries when they disagree.

## Reference notes

- See `references/open-source-infrastructure-editors.md` for a primary-source comparison of OSRD, JOSM/OSM/OpenRailwayMap, SUMO netedit, railVIVID, and an experimental MIT RailML editor.
- See `references/general-open-railway-ssot-formats.md` for IFC Rail, INSPIRE/OGC, OSM/GeoJSON, ERA RINF, RSM, and a layered-SSOT pattern.
- See `references/railml33-eulynx-dataprep.md` for primary-source findings on railML 3.3 versus EULYNX Data Preparation 1.2, including serialization, licensing, maintenance status, and SSOT suitability.
- See `references/general-open-railway-ssot-formats.md` for a primary-source comparison of IFC 4.3/IFC Rail, INSPIRE/GML, OSM/GeoJSON, ERA RINF, and RailTopoModel/RailSystemModel, including their interlocking-route boundaries.
- See `references/railml33-eulynx-dataprep.md` for specialist railML/EULYNX route and signaling-model details.
- See `references/railml33-runtime-contract-mapping.md` for the railML 3.3 static-to-runtime boundary, topology/asset/route mappings, exact state vocabularies, MQTT/API design guidance, and migration crosswalk checklist.