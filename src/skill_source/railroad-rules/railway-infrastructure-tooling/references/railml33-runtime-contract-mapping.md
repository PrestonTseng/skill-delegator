# railML 3.3 static-to-runtime contract mapping

Use this note when designing an operational simulator, PLC interface, HMI, or MQTT/API contract that should align with railML 3.3.

## Authoritative source

- Official schema repository: `https://development.railml.org/railml/version3`
- Session-inspected commit: `122180cfe2dc4485524e79caf6d110050ab356dd`
- Namespace/version: `https://www.railml.org/schemas/3.3`, XSD `3.3`
- Relevant files: `railml3.xsd`, `infrastructure3.xsd`, `rtm4railml3.xsd`, `interlocking3.xsd`, `generic3.xsd`

Re-inspect the current official source before relying on this pinned commit. Do not redistribute official schemas without checking current railML registration/license terms. Do not call an internal JSON/YAML representation “railML XML” or “certified railML.”

## Core boundary

railML 3.3 is suitable as the semantic reference for static engineering data. It does not by itself define a runtime transaction protocol.

Use two linked layers:

1. **Static railML-aligned model** — topology, infrastructure, interlocking assets, routes, conflicts, conditions, overlaps, releases, command/indication definitions.
2. **Application runtime extension** — telemetry timestamps/sequences, health, freshness, commanded versus observed state, command correlation/idempotency, ACK/result phases, MQTT QoS/retain, and simulation injection.

Every runtime state or command should reference a stable static object ID. Do not force runtime fields into railML native elements merely to claim format alignment.

## Topology mapping

- `Infrastructure.topology` contains `netElements`, `netRelations`, and `networks`.
- `NetElement` is a positioning network element with its own intrinsic positioning system.
- `NetRelation` connects `elementA` and `elementB` and carries `navigability`, `positionOnA`, and `positionOnB`.
- In a node/edge source model, a traversable segment usually maps toward `NetElement`; a graph vertex/junction usually drives one or more `NetRelation` records. Do not relabel graph vertices as `NetElement` without a semantic transformation.
- `Track` is a traversable, unbranched railway section and may aggregate/locate functional infrastructure.

## Infrastructure and interlocking dual representation

railML separates physical/functional infrastructure from interlocking use:

- Signal: `SignalIS` plus `SignalIL`.
- Switch: `SwitchIS` plus `SwitchIL`; switch branches refer to the `NetRelation` defining navigability.
- Physical detector/boundary: `TrainDetectionElement`.
- Track vacancy section: `TvdSection`, referring to demarcating detectors and covered track elements.
- Interlocking track: `TrackIL`, a named unbranched track length that may refer to TVD sections.
- WSS/interlocking: `SignalBox`.
- Field logic: `Controller` and/or `ObjectController`.

Never automatically equate an application “block,” `TrackIL`, and `TvdSection`. Confirm whether the object means an operational authority segment, an unbranched track length, or a vacancy-detection section.

## Route engineering data

Map static route data through:

- `Route` with `routeEntry`, `routeExit`, facing/trailing switch positions, `hasTvdSection`, and release groups.
- `ConflictingRoute` for explicit route conflicts.
- `RouteRelation` for required switch position, detector state, signal aspect, section vacancy, level-crossing state, and other enforced conditions.
- `Overlap` for protected track beyond the route, required switch positions, TVD sections, limits, and release timers.
- `RouteReleaseGroupAhead`, `RouteReleaseGroupRear`, and `RouteReleaseTrigger` for release engineering.

A runtime lifecycle such as aligning/proving/locked/active/releasing remains an application extension referring to the static `Route` ID.

## State vocabulary

- `tSwitchPosition`: `left`, `right`, `indifferent`.
- If the application uses `normal`/`reverse`, define the mapping separately for every switch. Never assume normal=left globally.
- `tSectionVacancy`: `occupied`, `unknown`, `vacant`.
- `tDetectorStates`: `activated`, `deactivated`, `inactive`.
- Detector triggering/availability and section vacancy are different state domains.
- Specific signal aspect IDs should link to railML `GenericAspect` classifications; keep commanded and observed/proved aspects distinct in runtime state.

## Commands and indications

- `OperatorCommand` and `Indication` define available vocabulary.
- Assets expose `hasCommand` and `hasIndication` references, optionally with an interface-specific `entityCode`.
- `extentOfControl` distinguishes `fullControl`, `notificationOnly`, `steeringOnly`, and `none`.

These declare capability and ownership. Runtime execution still needs fields such as:

- stable `command_id` across retries;
- `command_ref` and `target_ref`;
- issued timestamp/source/deadline;
- result phase (`received`, `accepted`, `rejected`, `completed`, `failed`, `timed_out`);
- stable reason code and achieved-state reference.

An acceptance ACK is not proof that a field state was achieved. Use observed state/indication to prove completion.

## Runtime transport design

Do not create one MQTT topic per railML class by default. Keep topic design based on delivery semantics and ownership:

- desired command/intention stream;
- command receipt/acceptance result;
- achieved-state snapshot or event stream;
- system/model-version information.

Commands must not be retained. QoS does not replace application-level idempotency and correlation. If latest state is retained, consumers must enforce timestamp/freshness before treating it as operationally current.

## Design checklist

1. Pin and inspect the official 3.3 XSD source used for the decision.
2. Create a deterministic crosswalk: source ID/field → railML element/property → application extension → legacy interface projection.
3. Mark unresolved mappings explicitly instead of inferring missing engineering facts.
4. Review topology transformation before renaming source nodes/segments.
5. Validate physical-vs-interlocking dual references.
6. Keep runtime and transport metadata outside the static railML layer.
7. Check registration, certification, commercial-use, derivative-work, and redistribution requirements before producing or shipping actual railML XML.
