# Open-source railway infrastructure authoring stacks

Use this reference when selecting a tool or canonical format for tracks, signals, turnouts, detectors, routes, and related field infrastructure. Re-verify current versions and licences before adoption.

## Recommended evaluation order

### OSRD + RailJSON — strongest immediate authoring fit

OSRD is an open-source web application with infrastructure-editor tools for tracks, track splits, speed sections, electrification, switches, signals, detectors, buffer stops, and routes. RailJSON supports complete infrastructure import and serialization.

Its topology model is the key advantage:

- a switch has named ports;
- a switch type defines groups of permitted port-to-port connections;
- built-in types include ordinary point switch, crossing, single slip, and double slip;
- routes record entry/exit, direction, release detectors, and required switch positions.

Recommended workflow:

1. Keep a pinned RailJSON file in Git as the canonical artifact.
2. Import it into a self-hosted OSRD instance as an editable working copy.
3. Export after editing.
4. Run schema and semantic validation.
5. Review deterministic diffs before commit.

Do not make the OSRD database the only source. RailJSON is application-specific, and OSRD states that its user/programming interfaces are still evolving.

Primary sources:

- OSRD repository and status/licence: https://github.com/OpenRailAssociation/osrd
- Editor tools: https://github.com/OpenRailAssociation/osrd/blob/dev/front/src/applications/editor/tools/constsTools.ts
- Infrastructure model: https://github.com/OpenRailAssociation/osrd/blob/dev/core/osrd-railjson/src/main/java/fr/sncf/osrd/railjson/schema/infra/RJSInfra.kt
- Switch ports and transition groups: https://github.com/OpenRailAssociation/osrd/blob/dev/core/osrd-railjson/src/main/java/fr/sncf/osrd/railjson/schema/infra/RJSSwitchType.kt
- Routes: https://github.com/OpenRailAssociation/osrd/blob/dev/core/osrd-railjson/src/main/java/fr/sncf/osrd/railjson/schema/infra/RJSRoute.kt
- Import/export API: https://github.com/OpenRailAssociation/osrd/blob/dev/editoast/src/views/infra/railjson.rs
- Programmatic generator: https://github.com/OpenRailAssociation/osrd/blob/dev/python/railjson_generator/README.md

### railML 3.x + RailTopoModel — interchange target, not default authoring stack

railML supplies infrastructure and interlocking subschemas in XML/XSD. RailTopoModel is the generic topology basis for railML 3.x. This is broader than RailJSON for industry interchange, but official open tooling is mainly railVIVID, a viewer/validator rather than an editor.

Important licensing caveat: railML 3.x and RailTopoModel publish adapted CC-BY-NC-ND terms and impose implementation/registration or certification conditions. Do not copy their schema into a commercial internal model without current legal/licensing review. Prefer railML as a future exporter when a customer or partner requires it.

Primary sources:

- https://www.railml.org/en/about-railml
- https://www.railml.org/en/subschemas
- https://www.railml.org/en/licence
- https://www.railml.org/en/railvivid
- https://www.railtopomodel.org/railtopomodel

### JOSM + OpenStreetMap/OpenRailwayMap — geometry and asset capture

JOSM and OpenRailwayMap presets cover geographic tracks, signals, switches, crossings, and many railway attributes. OSM exports XML, PBF, and JSON variants.

Use this stack for survey geometry or asset inventory, not as the authoritative operational model. OSM's generic nodes/ways/relations plus tags do not natively supply explicit switch-transition groups, route switch states, release detectors, route conflicts, or flank-protection semantics.

OSRD includes an OSM-to-RailJSON converter, but its documentation warns that angle-based switch-branch inference can produce false positives and that generated signalling/routes contain assumptions. Treat conversion as bootstrap data requiring manual validation.

Primary sources:

- https://github.com/OpenRailwayMap/OpenRailwayMap
- https://github.com/OpenRailwayMap/OpenRailwayMap/blob/master/josm-presets/infrastructure.xml
- https://wiki.openstreetmap.org/wiki/Key:railway
- https://github.com/OpenRailAssociation/osrd/blob/dev/editoast/osm_to_railjson/README.md
- https://github.com/OpenRailAssociation/osrd-website/blob/master/content/docs/reference/design-docs/osm-to-railjson/index.en.md

### SUMO netedit — simulation/export target

SUMO netedit graphically edits rail networks and writes XML. It supports rail signals, routes, bidirectional tracks, crossings, and simulation. Do not use it as the canonical operational infrastructure model: official documentation lists gaps such as unmodelled signal overlap and shunting/reversal restrictions.

Primary sources:

- https://github.com/eclipse-sumo/sumo/blob/main/docs/web/docs/Netedit/index.md
- https://github.com/eclipse-sumo/sumo/blob/main/docs/web/docs/Simulation/Railways.md

## Canonical-model validation checklist

A candidate canonical file should support and validate:

- stable unique IDs and referential integrity;
- track geometry and endpoint connectivity;
- named switch/trackwork ports;
- only physically permitted transitions for each point position;
- signal and detector locations within track bounds;
- route continuity, direction, release points, and required switch states;
- route conflicts, flank protection, and clearance constraints, through extensions if necessary;
- deterministic import → edit → export round trips;
- adapters for downstream consumers rather than duplicated hand-maintained files.

Never infer trackwork semantics from graph degree alone. Geometry-based inference is useful only for generating a draft that is subsequently reviewed.