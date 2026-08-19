# railML 3.3-SR2 static WSS/PLC topology profile

Use this reference when reviewing or replacing TAPAS WSS/OpenPLC topology YAML against railML 3.3-SR2.

## Design verdict

Do not keep extending a parallel `vertex -> sub_block -> block` graph. Use railML's native separation:

1. **Infrastructure / RTM:** `netElement`, `netRelation`, positioning systems, and physically located wayside assets.
2. **Interlocking:** `tvdSection`, `switchIL`, `signalIL`, `route`, `routeRelation`, `conflictingRoute`, `overlap`, and route-release groups/triggers.
3. **TAPAS extensions:** only concepts with no adequate railML element, explicitly labelled and kept separate from native fields.

This is a semantic alignment profile, not a requirement to author XML. Human-reviewed YAML may remain the SSOT and compile deterministically to railML-shaped JSON/XML and later PLC contracts.

## Minimal native mapping

- `sub_block` -> `netElement`.
- `vertex` -> remove; connect `netElement` endpoints using `netRelation.elementA/elementB`, `positionOnA/positionOnB` (`0|1`), and `navigability` (`AB|BA|Both|None`).
- ambiguous `block` -> `tvdSection` when it means a vacancy-detection section; `track` when it means a continuous named track. Do not retain an undefined generic block layer.
- signal -> physical `signalIS` with `spotLocation` and physical capability flags such as train-movement/switchable, plus logical `signalIL` referencing it and owning operational function/allowed semantic aspect IDs.
- switch -> physical `switchIS` branches referencing `netRelation`, plus `switchIL` for interlocking behavior. One `switchIL` may reference one or two `switchIS` assets where the SR2 cardinality permits applicable switch/crossing arrangements. Use railML `left|right|indifferent`, not ungrounded `NORMAL|REVERSE`.
- detection section -> physical `trainDetectionElement` delimiters plus logical `tvdSection.hasTrackElement` membership. Detection technology belongs to `tvdSection`, not to the physical boundary element.
- per-segment speed -> `speedSection` with a linear location, not a property copied onto every topology edge.
- route -> split into native route path/resources, route conditions, conflicts, overlap, and release objects.
- platform/yard vertex flags -> native `platformEdge` / `operationalPoint` / track classification; never booleans on a graph junction.

## Core profile

Require:

- one pinned linear positioning system;
- each `netElement` to have a stable ID, length, and begin/end measures mapped to intrinsic coordinates `0` and `1`;
- one explicit `netRelation` for each traversable end-to-end connection;
- one network level containing the canonical `netElement` set;
- explicit locations for all physical assets;
- `tvdSection` membership to be the single occupancy grouping truth;
- route path to use TVD sections, with physical continuity validated through `netRelation`.

Conditional native asset families such as buffer stops, crossings, derailers, level crossings, balises, operational points, and platform edges are present only when the reviewed inventory contains them. Omit absent containers; do not invent objects or use empty lists to assert an unresolved inventory.

## Trackwork rules

- Graph degree never identifies a physical switch or crossing.
- A turnout or slip must name its branch relation IDs.
- A diamond crossing permits only its two straight-through route pairs.
- Special trackwork is represented by ports plus permitted transitions, not a complete graph.
- railML `switchIS` supports left/right branches for an ordinary switch and straight/turning branch choices for switch-crossing arrangements.

## Interlocking decomposition

### TVD section

Store static engineering membership and delimiters only:

- `hasTrackElement` net-element references;
- demarcating train detectors, buffer stops, or exit signals;
- technology (`axleCounter`, `trackCircuit`, or reviewed extension);
- reviewed static release/cancellation delays when applicable.

Do not put initial occupancy, health, or freshness into static topology. railML vacancy semantics are `occupied|unknown|vacant` and belong in route conditions or runtime state.

### Route and protection

- `route`: entry, exit, TVD sections, facing/trailing switch positions, release groups, and relation references.
- `routeRelation`: typed switch positions, section vacancy, signal aspects, and other native condition tuples.
- Flank protection: reference a route relation with railML relation usage `inFlankProtection`; avoid generic `asset_type/id/state` unions.
- `conflictingRoute`: define each conflict set once rather than copying reciprocal route-ID arrays.
- `overlap`: independent resource with TVD sections, switch requirements, limits, release rules, and applicable approach routes.
- `routeReleaseGroupAhead` and `routeReleaseGroupRear` are distinct typed partial-route objects. Use their ordered TVD memberships, delay/automatic fields where applicable, and `RouteReleaseTrigger` for final release. Do not collapse them into an untyped generic group or store imperative per-step lists of switches and blocks to unlock.

## Static-boundary exclusions

Move these out of topology and into later `simulation_defaults`, `runtime_state`, PLC parameter, or interface-binding artifacts:

- all `initial_*` fields;
- current aspect, position, occupancy, direction, health, and route lifecycle;
- freshness/staleness values;
- MQTT/Modbus addresses and live values;
- legacy numeric interface codes;
- legacy `NORMAL/REVERSE` mappings;
- duplicated command/proof/release workflows.

A reviewed throw time or interlocking release delay may be static engineering data. A simulator startup state is not.

## TAPAS extensions

Keep extensions in a visibly separate namespace/section. Candidate extensions:

- source provenance and immutable artifact hashes;
- `railml_release: 3.3-SR2` in addition to native `railml_version: 3.3`;
- read-only display coordinates in a separate visualization overlay;
- a traffic-direction-lock resource only if WSS needs a standalone ABS direction lock that cannot be derived from routes/conflicts. Express direction relative to canonical A/B orientation, and exclude current/initial direction state.

Prefer native `designator` over a custom aliases field. Before retaining any extension, document why no railML 3.3-SR2 element is adequate.

## XSD review checklist

Inspect the pinned SR2 distribution directly, especially:

- `railml3.xsd`: root infrastructure/interlocking and `railML/@version`;
- `infrastructure3.xsd`: `Topology`, `NetElement`, `NetRelation`, `FunctionalInfrastructure`, `SwitchIS`, `SignalIS`, `TrainDetectionElement`, `SpeedSection`;
- `rtm4railml3.xsd`: `RTM_AssociatedPositioningSystem`, `RTM_PositioningNetElement`, `RTM_Relation`, `RTM_SpotLocation`, `RTM_LinearLocation`, `tNavigability`, `tUsage`;
- `interlocking3.xsd`: `AssetsForInterlocking`, `TvdSection`, `SwitchIL`, `SignalIL`, `Route`, `RouteRelation`, `ConflictingRoute`, `Overlap`, `RouteReleaseGroupRear`, `RouteReleaseTrigger`, `tSwitchPosition`, and `tSectionVacancy`.

Do not infer schema semantics from type names alone. Read base-type inheritance, required children, cardinalities, enumerations, and XSD documentation. When producing a review, cite XSD file, type/element, and line range or extracted schema revision.

## Review output

A useful review should provide:

1. short verdict;
2. current-to-railML mapping;
3. exact minimal native entity/field profile;
4. conditional asset families;
5. native versus TAPAS-extension table;
6. fields removed from static topology;
7. migration disposition for every existing schema file;
8. pinned XSD citations.
