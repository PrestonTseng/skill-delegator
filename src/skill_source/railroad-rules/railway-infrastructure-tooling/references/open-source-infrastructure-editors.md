# Open-source railway infrastructure editors

Use this note when comparing graphical tooling for railway infrastructure definitions. Re-check upstream sources before reporting versions or current capabilities.

## Evaluation frame

For each tool, distinguish:

1. **Authoring surface** — geographic assets, schematic topology, simulation network, or operational/interlocking data.
2. **Native persistence/export** — do not equate an import path with round-trip export.
3. **Software license vs data/schema license** — editor code, map data, and exchange schema may have different terms.
4. **Route meaning** — an OSM railway route, train itinerary, simulation route, and interlocking route are not equivalent.
5. **Interlocking completeness** — inspect entry/exit, required point positions, release sections, route conflicts, overlap, flank protection, and locking/release logic.
6. **Claims vs serialization** — verify README claims against schema/model source and emitted namespaces.

## Evidence-backed snapshot (2026-08)

### OSRD Infrastructure Editor

- Open-source web application for infrastructure design, capacity analysis, timetabling, and simulation; LGPL-3.0-only.
- Editor source exposes tools for track creation/splitting, speed sections, electrification, switches, signals, detectors, buffer stops, and routes.
- Imports/exports OSRD RailJSON. Its schema covers operational points, routes, switch types, switches, track sections, speed/electrification/neutral sections, signals, detectors, buffer stops, and level crossings.
- A serialized route has entry/exit waypoints, entry direction, release detectors, and switch directions.
- Stronger operational semantics than GIS tools, but serialized Route lacks explicit route-conflict tables, overlap, and flank-protection fields. Do not describe it as a complete interlocking engineering model without further evidence.

Primary sources:
- https://github.com/OpenRailAssociation/osrd
- https://github.com/OpenRailAssociation/osrd/blob/dev/front/src/applications/editor/tools/constsTools.ts
- https://github.com/OpenRailAssociation/osrd/blob/dev/editoast/schemas/src/infra/railjson.rs
- https://github.com/OpenRailAssociation/osrd/blob/dev/editoast/schemas/src/infra/route.rs
- https://github.com/OpenRailAssociation/osrd/blob/dev/editoast/src/views/infra/railjson.rs
- https://osrd.fr/en/docs/reference/design-docs/signaling/
- https://osrd.fr/en/docs/reference/design-docs/signaling/blocks-and-signals/
- https://osrd.fr/en/docs/reference/design-docs/signaling/simulation/

### JOSM / OpenStreetMap / OpenRailwayMap

- JOSM edits OSM nodes, ways, relations, and tags; saves OSM/XML/PBF and GeoJSON among other formats.
- OpenRailwayMap is principally a renderer and railway-tagging ecosystem over OSM data, not the editor itself.
- Code/data licenses differ: JOSM GPL-2.0-or-later, OpenRailwayMap GPL-3.0, OSM data ODbL.
- Railway tagging covers assets such as tracks, switches, signals, detectors, signal boxes, and interlocking ranges.
- `route=railway` relations describe railway lines or routes of operation, not signal-to-signal locking routes. OSM tagging does not constitute a route-locking/conflict/flank/release model.

Primary sources:
- https://josm.openstreetmap.de/wiki/Introduction
- https://josm.openstreetmap.de/wiki/Help/Action/Save
- https://github.com/JOSM/josm/blob/master/LICENSE
- https://wiki.openstreetmap.org/wiki/OpenRailwayMap
- https://wiki.openstreetmap.org/wiki/OpenRailwayMap/Tagging
- https://www.openstreetmap.org/copyright

### SUMO netedit

- Graphical editor for SUMO networks. Edits edges, junctions, connections, prohibitions, traffic lights/rail signals, demand routes, and other simulation objects.
- Inputs include SUMO network files, OSM, and netconvert configurations; outputs SUMO `.net.xml` and plain XML. netconvert supports additional conversion formats.
- SUMO is EPL-2.0.
- Railway simulation supports `rail_signal`, block/driveway behavior, bidirectional-track handling, deadlock logic, and schedule constraints.
- These are simulation semantics, often generated or heuristic; do not equate them with an auditable interlocking locking table.
- railML.org lists railML 2.5 infrastructure/timetable **import** as uncertified. Current netedit/netconvert format documentation does not establish railML export.

Primary sources:
- https://sumo.dlr.de/docs/Netedit/index.html
- https://sumo.dlr.de/docs/Simulation/Railways.html
- https://sumo.dlr.de/docs/Networks/PlainXML.html
- https://sumo.dlr.de/docs/netconvert.html
- https://github.com/eclipse-sumo/sumo/blob/main/LICENSE
- https://www.railml.org/en/software/sumo

### `keepsky/Railml_editor`

- Young Windows WPF graphical editor under MIT; README claims RailML 2.5 persistence for tracks, signals, switches, and complex routes.
- Source includes route fields for entry/exit, point positions, overlap, release sections, and a flank-protection flag.
- Critical limitation: source labels its model “Simplified RailML 2.5,” and serializes routes/areas/release data in `http://www.sehwa.co.kr/railml`, a custom namespace. Treat as an experimental editor, not proven standard railML interlocking interchange.
- Check railML.org certification registry before asserting interoperability.

Primary sources:
- https://github.com/keepsky/Railml_editor
- https://github.com/keepsky/Railml_editor/blob/main/LICENSE
- https://github.com/keepsky/Railml_editor/blob/main/RailmlEditor/ViewModels/Elements/RouteViewModel.cs
- https://github.com/keepsky/Railml_editor/blob/main/RailmlEditor/Services/Mappers/RouteMapper.cs
- https://github.com/keepsky/Railml_editor/blob/main/RailmlEditor/Models/RailModel.cs

### railVIVID and railML licensing

- railVIVID is an official viewer/validator, not an infrastructure authoring editor.
- It supports visualization and schema/partial-semantic validation across railML subschemas.
- Official wording says key source modules will be made open source later; current distribution is freeware under dedicated terms, not a demonstrated OSI-open editor.
- railML schemas, documentation, examples, and railVIVID have separate license conditions. Verify registration, NC/ND, certification, and commercial-use requirements rather than assuming “open language” means unrestricted open-source software.

Primary sources:
- https://www.railml.org/en/railvivid
- https://www.railml.org/en/software/railvivid
- https://www.railml.org/en/licence

## Reporting pattern

Prefer a compact table with columns: tool/role; authoring; native import/export; software and data/schema license; interlocking-route capability; decisive limitation.

End with a recommendation by use case. For a true infrastructure SSOT, separate geographic assets from operational/interlocking semantics, and explicitly model port transitions, required point positions, conflicts, overlap, flank protection, and release logic.