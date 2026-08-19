# General/open formats for a railway-site SSOT

Use this note when comparing general infrastructure/GIS/registry models against safety-critical interlocking semantics. Primary sources only.

## IFC 4.3 / IFC Rail

- **Covers:** openBIM engineering geometry and asset structure: alignments, railway spatial decomposition, track components, signals, cables, assemblies, properties and positioning.
- **Does not establish by itself:** executable interlocking route tables, required point positions, locking/release timing, overlap/flank protection, or route-conflict matrices. `IfcSignal` may group signaling equipment logically, but that is not proof of route-locking semantics.
- Official IFC 4.3.2.0: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/
- Rail domain: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/ifcraildomain/content.html
- `IfcSignal`: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcSignal.htm

## OGC / INSPIRE Transport Networks

- **Covers:** harmonized GIS transport-network publication. Railway schema includes links, link sequences, nodes, station/yard nodes and areas, railway lines, design speed, nominal gauge, number of tracks, electrification and use. INSPIRE sets GML (ISO 19136) as its default encoding.
- **Lacks for interlocking:** microscopic route application data, switch-position requirements, locking/release rules, overlap/flank protection, and conflict matrices.
- Official technical guideline: https://inspire-mif.github.io/technical-guidelines/data/tn/dataspecification_tn.html

## OpenStreetMap / OpenRailwayMap and GeoJSON

- **OSM covers:** node/way/relation plus free-form tags; railway tagging includes tracks, switches, signals, detectors, operating sites, and an interlocking control-area relation whose members may include controlled signals and switches.
- **Critical distinction:** `route=railway` describes a railway operating route/line, not a signal-to-signal interlocking route. The interlocking relation identifies control scope, not route tables or conflicts. OSM has conventions rather than a closed mandatory ontology.
- OSM elements: https://wiki.openstreetmap.org/wiki/Elements
- OpenRailwayMap tagging: https://wiki.openstreetmap.org/wiki/OpenRailwayMap/Tagging
- **GeoJSON covers:** generic Point/LineString/Polygon/Feature/FeatureCollection interchange in WGS 84. RFC 7946 explicitly implies no particular service model or feature ontology; railway and interlocking semantics must therefore come from an external schema.
- GeoJSON RFC 7946: https://datatracker.ietf.org/doc/html/rfc7946

## ERA RINF / ERA Ontology

- **Covers:** EU regulatory register of static-network Operational Points, Sections of Line and subsystem/network parameters; also supports route compatibility checks for whether a vehicle can travel between operational points. The ERA Ontology supplies RDF/OWL serializations, JSON-LD, TTL and SHACL.
- **Critical distinction:** RINF Route Compatibility Check is vehicle/infrastructure compatibility, not an interlocking route. RINF does not provide station route-locking logic or conflict matrices.
- RINF: https://www.era.europa.eu/domains/registers/rinf_en
- ERA Ontology: https://rinf.data.era.europa.eu/vocabulary/

## RailTopoModel / RailSystemModel

- **Covers:** UIC generalist, scalable railway topology/system backbone across topology, position, geometry, lifecycle and multiple railway domains. RailTopoModel is now RailSystemModel (RSM).
- **Boundary:** UIC explicitly describes RSM as generalist and identifies EULYNX as the signaling expert-model example. Use RSM for cross-domain identity/topology, but do not assume the core contains complete interlocking route, locking/release and conflict semantics.
- UIC history/version page: https://uic.org/rail-system/railsystemmodel
- Current RSM overview: https://rsm.uic.org/

## Recommended layered SSOT pattern

Use stable canonical identifiers and link rather than flattening all meanings into one file:

1. RSM or a canonical graph for identity and topology;
2. IFC for engineering geometry and asset/BIM views;
3. RINF for EU regulatory/interoperability views;
4. INSPIRE, OSM and GeoJSON for GIS/publication projections;
5. a specialist signaling model for `route -> required points/signals/track sections -> overlap/flank protection -> locking/release -> conflicts`.

Negative findings must be worded narrowly: state that the cited official schema does not define an explicit construct, rather than claiming the format can never carry an extension.