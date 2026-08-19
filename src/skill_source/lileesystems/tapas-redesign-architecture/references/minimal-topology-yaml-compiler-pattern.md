# Minimal topology YAML compiler pattern

Use this reference when a TAPAS redesign task asks for one graph-friendly YAML source that can generate railML XML, shared JSON, and OpenPLC Structured Text.

This is a review pattern, not an approved TAPAS platform contract. Re-read the current design page, ADR status, live ICD, and engineering values before implementation.

## Design boundary

Keep one logical, versioned YAML model as the only authored source. A loader can merge several physical YAML files, but file boundaries must not change the semantic model.

Compile authoring YAML into one immutable semantic intermediate representation (IR). Every exporter reads the IR directly:

```text
YAML -> parse/schema checks -> reference/graph checks -> semantic IR
                                                    |-> railML XML
                                                    |-> shared JSON
                                                    |-> OpenPLC ST + symbol/binding maps
```

Never parse one generated product to create another product.

An authoring graph may retain domain-friendly `vertex` and `sub_block` names when the reviewer wants them for graph computation. The IR must still contain one connectivity truth: lower sub-blocks to semantic `NetElement` objects and validated endpoint/switch transitions to semantic `NetRelation` objects. Do not maintain a second parallel graph.

## KISS rules

- Define each fact once.
- Keep stable, globally unique IDs.
- Use references, not nested copies.
- Keep runtime values and command instances out of topology YAML.
- Keep design evidence in review documents, commits, and change records; do not add `source`/`source_refs` fields or a source-note catalog to the formal topology schema unless the user explicitly requires machine-readable provenance.
- Use `null` for unknown inventory and reject deployable generation; use `[]` only for a reviewed empty inventory.
- Derive adjacency, indexes, route block lists, ordinary conflicts, IEC symbols, and consumer views.
- Keep safety intent explicit: ordered route path, switch positions, overlap, flank protection, release triggers/partitions, and exceptional conflicts.
- Do not add a generic expression language or free-form property bag.
- Reject unresolved safety data before railML/ST deployment artifacts are generated.

## Current minimum review baseline

A clean current review baseline has 10 wayside element classes:

1. `vertex`
2. `sub_block`
3. `block`
4. `stopping_place`
5. `switch`
6. `detection_section`
7. `signal`
8. `marker`
9. `route`
10. `direction_lock`

Use catalogs for `site`, `lines`, `tracks`, `signal_aspects`, and true site-wide `policies`. Protocol-ID conversion is owned by each service adapter and is not a topology catalog or compiler output.

Treat `service_patterns` and `timing_profiles` as operational catalogs, not wayside element classes.

This is a review baseline, not a frozen universal list. Add another element only when current inventory and behavior justify an independent identity, lifecycle, or projection.

## Modeling choices

### Line and track

A line contains one or more physical tracks. Existing labels such as `AV`, `ET`, and `WT` behave as tracks, not lines.

- `line.track_refs` owns membership.
- `track.line_ref` can be generated or validated according to the chosen normalization, but do not create two conflicting membership truths.
- The line owns one explicit linear positioning system and unit; canonical infrastructure positions use `milepost_m` in that system.
- `sub_block.track_ref` points to a track; endpoint mileposts define the sub-block's linear extent and direction.
- Project line, track, positioning, and sub-block ranges into railML objects.
- Convert protocol-specific milepost encodings in service adapters. For example, TAPAS Type 2's one-tenth-metre integer is an adapter representation, not the canonical topology unit.

### Vertex and sub-block

- A vertex is a zero-length graph endpoint or junction; it is not a stopping area.
- A sub-block is the smallest edge at a junction, detection boundary, operational-stop boundary, or speed boundary.
- A degree-greater-than-two vertex requires explicit switch transitions; graph degree cannot prove a physical switch or all-to-all connectivity.
- Each sub-block owns one block reference. Do not repeat ordered sub-block lists in blocks.

### Block and occupancy

A block is the canonical occupancy, authorization, status, and display target.

Derive occupancy conservatively:

- `occupied` if any contributing detection section is occupied
- `vacant` only if every contributing section is healthy and vacant
- `unknown` otherwise.

The live TAPAS ICD Type 13 payload carries `BlockStat{Name, Occupancy}`. Treat the target as the canonical block ID. Type 19 is status/version data, not occupancy.

Any protocol-name conversion remains local service business logic. Do not add a second occupancy-object ID or a canonical mapping catalog.

### Stopping place

Keep generic station, yard, depot, and platform grouping out of the topology SSOT unless a safety or infrastructure requirement proves it belongs there. Those groupings normally belong to service, timetable, or UI models.

Represent the train stop as a graph-attached railway point:

```yaml
stopping_places:
  - id: STOP-N2WN
    sub_block_ref: SB-H1T-R
    milepost_m: 1400.5
```

- `sub_block_ref` attaches the stop to the graph edge used by route and mission consumers.
- `milepost_m` is authoritative in the line's linear positioning system.
- Derive `track_ref` from the sub-block; do not repeat it.
- Validate that the milepost lies between the referenced sub-block endpoint mileposts.
- Project this to railML `StoppingPlace` at the linear coordinate.
- Do not author `from_offset_m`/`to_offset_m` for a point stop. If a physical platform edge or stopping tolerance is later required, model it as a separately reviewed linear feature rather than inferring it from a station object.

### Switch

For an ordinary turnout, use railML-native canonical positions `left | right`; do not define a second `normal/reverse` enum or custom `toward-*` IDs.

```yaml
switches:
  - id: SW-01
    vertex_ref: V-J01
    tip_sub_block_ref: SB-IN
    positions:
      left:
        branch_sub_block_ref: SB-LEFT
      right:
        branch_sub_block_ref: SB-RIGHT
```

Commands, feedback, route proof, and flank protection use `position: left | right`. From the same facts, deterministically generate:

- tip↔left and tip↔right `NetRelation` objects
- `SwitchIS.leftBranch/rightBranch`
- `SwitchIL.branchTip/branchLeft/branchRight`
- route/protection `SwitchAndPosition.inPosition`.

Hardware normal/reverse bits belong in the service adapter and must not be written back to topology. Validate all three distinct sub-blocks as incident to the switch vertex. Do not assume geometry can safely reconstruct left/right if the canonical data omits it.

### Crossing and platform doors

Do not include `crossing` or `platform_door` merely because a broad railML profile or old design listed them.

- A fixed diamond with no traversal between tracks can be represented by two non-connecting graph paths.
- If it needs shared interlocking protection, routes can declare reviewed explicit conflicts until the site proves that an independent crossing resource/lifecycle is needed.
- Platform doors remain out of the minimum topology/command contract until their current requirement and owner are in scope.

### Route, overlap, flank, and release

A route authors one ordered sub-block path and explicit protection intent.

Overlap must define:

- path beyond the route exit
- required switch positions
- detection/proof inputs
- release trigger, transition, and timing.

Flank protection must define:

- protected resource
- required proved state
- the sectional/final release partition that releases it.

`release_through_sub_block_ref` can compactly release eligible path resources. Non-path, overlap, and flank resources must be named in explicit release sets.

Validate that every acquired resource occurs in exactly one sectional or final release partition. A timer alone cannot release protection while occupancy or health is unknown.

### Direction lock instead of ABS route lists

Avoid duplicating route-family lists in a TAPAS-specific `abs_territory` object.

Use a generic exclusive `direction_lock` resource with allowed values such as `increasing` and `decreasing`. Each route declares one lock reference and value. The compiler groups routes by lock and derives opposite-value conflicts.

TAPAS target lifecycle:

1. The first route-setting transaction acquires the free lock in its required value.
2. The route cannot be proved or clear its signal until that value is achieved.
3. Same-value routes may share ownership.
4. Opposite-value routes remain blocked while any owner or protected occupancy exists.
5. Return to `free` only after the last owner releases and the detection coverage derived from the lock's route paths is safely vacant.

Do not expose a public `set_direction_lock`. A protected maintenance recovery may clear a stale lock after owner/vacancy checks but must not choose a running direction. Some railway products provide operator block-direction controls, but that system-specific workflow does not justify an unproved generic setter in TAPAS.

## Operational catalogs

Include reviewed service-pattern and timing catalogs when Thalos mission composition and Unicorn schedule/conflict views must share the same authored basis.

- A service pattern references ordered routes and stop places.
- A timing profile contains positive, reviewed segment times.
- Runtime mission/timetable instances reference these catalogs; they do not copy expanded topology.
- Sentinel values such as `-99999` mean unknown and block deployable timing artifacts.

## Runtime and command boundary

Generate command and state JSON Schemas from fixed capabilities. Do not store command instances or live states in topology YAML.

Normal public operations:

- side-effect-free `check_route`
- `request_route`
- `cancel_route`.

Privileged/internal operations can include:

- `reset_route`
- controller `recovery_reset`
- `set_switch_position(position: left | right)`
- `set_signal_aspect`
- simulator-only detection injection.

Do not include a platform-door command when platform doors are out of scope.

A command result separates `accepted` from `completed` and names a stable achieved condition. OpenPLC rechecks safety conditions; a previous eligibility query cannot authorize a command. Independent feedback proves achieved state.

Every static bundle, command, result, and state record carries the same `model_hash`; reject unknown hashes.

## Consumer views

Generate one normalized JSON bundle. Consumers select views instead of maintaining copied topology; protocol-ID conversion remains private service business logic:

- WSS/OpenPLC: routes, resources, commands, states, and PLC symbols
- Thalos: graph, routes, signals, block occupancy, direction locks, service patterns, timing profiles
- Unicorn: graph positions, stopping places, routes, conflicts, service patterns, timing profiles
- ADS: line, track, milepost, sub-block, block, and geography
- TriOps: Type 13 block occupancy against canonical block IDs.

ICD payloads are transport adapters, not the static topology source.

## railML projection

Do not copy the railML XML hierarchy into YAML. Validate generated XML against the pinned SR2 XSD.

Typical projections:

- line/track catalogs and endpoint `milepost_m` values -> `Line`, `Track`, and `LinearPositioningSystem`
- sub-block -> `NetElement` and track ranges
- degree-two endpoints and explicit switch transitions -> `NetRelation`
- contiguous equal sub-block speed values -> `SpeedSection`
- stopping place -> `StoppingPlace` at the referenced linear coordinate; do not invent `OperationalPoint`/`PlatformEdge`
- switch tip/left/right facts -> `SwitchIS.leftBranch/rightBranch`, `SwitchIL.branchTip/branchLeft/branchRight`, and route `SwitchAndPosition`
- detection -> `TvdSection` / detector limits
- signal -> `SignalIS` / `SignalIL`
- route -> route body, overlap, flank, release groups, and conflicts
- direction lock -> incompatible route conflicts, not a TAPAS-specific railML object.

Keep TAPAS commands, health, freshness, controller recovery, and mission instances outside railML XML.

## OpenPLC projection

Generate a logical I/O inventory before target binding. Record channel, authority, type, and fail-safe value. A simulator may write field-feedback inputs but not route ownership or command results.

Generate deterministic IEC symbols, then allocate target addresses through an append-only `bindings.lock.json` and publish `openplc-map.json`.

- First allocation uses a documented deterministic order.
- Later allocations preserve existing logical IDs and append new bindings.
- Topology YAML contains no Modbus registers, IEC locations, hardware switch bits, or target symbols.
- Prove exact IEC-to-Modbus mapping against the deployment image.
- Use one contiguous FC16 command envelope with correlated sequence and separate result/achieved-state words.

Require deterministic regeneration, pinned compiler acceptance, shared `model_hash`, restrictive startup, stale/unknown fail-safe behavior, command-versus-achieved proof, route conflict/protection/release tests, and first/last/highest address probes.

## Review gate

Before ADR amendment or implementation, ask the reviewer to decide:

- exact element and catalog set
- line/track hierarchy
- sub-block boundary rule
- place spans and stop positions
- canonical switch position identity
- whether crossing/platform doors are actually in scope
- route overlap, flank, and complete release partition
- direction-lock semantics
- service/timing catalog scope
- external ID mappings and TriOps block IDs
- append-only PLC binding ABI
- unresolved switch, detection, signal, route, protection, release, and timer values.
