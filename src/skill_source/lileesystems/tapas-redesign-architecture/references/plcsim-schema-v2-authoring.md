# plcsim schema v2 authoring and validation

Use this reference when revising the railML-aligned TAPAS engineering YAML contract or producing connected examples.

## Canonical boundaries

- The authored YAML is an internal canonical engineering model aligned with a declared railML 3.3 profile; it is neither railML XML nor a PLC runtime contract.
- Keep runtime/initial values, owners, health/freshness, timestamps, MQTT/Modbus bindings, PLC symbols, and protocol codes outside static schemas.
- Keep `vertex` and `sub_block` as the graph-friendly physical topology model. A sub-block identifies track, endpoints, endpoint mileposts, and navigability.
- Define block membership once in `blocks[].sub_block_refs`; do not also author `sub_block.block_ref`.
- In the approved TAPAS profile, `block` is the single logical vacancy-detection and occupancy identity and projects to railML `TvdSection`. Do not create a parallel `detection_section` document. Add separately identified physical train-detection elements only when device-level simulation or binding is required.

## Point and range semantics

- `sub_block_ref + milepost_m` is a point location.
- A `stopping_place` is an operational stop point, not a platform or stopping extent.
- Cardinality is many stopping places to one sub-block: each stopping place resolves to one sub-block, while a sub-block may contain zero or many stopping places.
- If an extent is required, add a separately reviewed start/end range, tolerance, stopping zone, or platform edge. Never overload one milepost scalar to imply length.
- Derive track identity from the referenced sub-block rather than authoring it twice.

## Routes and interlocking resources

- A route authors one ordered sub-block path. Derive its acquired logical blocks through authoritative block membership; do not author a second `block_refs` route path.
- Model route conditions, independent conflicts, overlaps, and release groups as separate typed documents.
- Use route conflicts only for independent static conflicts such as incompatible switch positions or flank protection. Do not duplicate opposite-direction exclusion as pairwise route conflicts when a shared direction lock already owns that invariant.
- A static route may require `direction_lock_ref + direction`. Same-direction routes can share the runtime lock; opposite direction is exclusive.
- Static direction-lock data defines territory coverage and allowed directions only. Runtime value, owners, pending authorities, restart recovery, vacancy/health/freshness proof, and release lifecycle belong to runtime state.
- Derive overlap block coverage from its ordered sub-block path.
- Ensure each route-owned block is released by exactly one referenced release group. Validate trigger and released-resource references.

## Example design

- Provide one connected, fictitious `EX-*` example document per independently authored data schema.
- Include examples that prove: point stopping places; a three-leg turnout; a station/branch route; same-direction lock sharing; opposite-direction exclusion; an independent switch-position conflict; overlap release; and complete release partitioning.
- `common` and `enums` are schema libraries, not independently authored data documents. Give important `$defs` examples in the schemas and exercise them through document examples.
- Keep the real `data/` absent when the user explicitly wants to refill it from accepted examples. Test this absence so old data cannot silently return.

## Verification gates

Run all of these before publishing:

1. YAML parse for every schema and example.
2. Draft 2020-12 metaschema validation for every schema, including libraries.
3. Each document example against its corresponding schema.
4. Global ID uniqueness and all cross-document references.
5. Track/vertex/sub-block integrity and exact single block membership.
6. Point locations within referenced sub-block milepost bounds.
7. Switch legs are three distinct sub-blocks incident on the switch vertex.
8. Ordered route and overlap path continuity.
9. Derived route/overlap block coverage.
10. Direction-lock coverage and allowed direction values.
11. Route condition/conflict/overlap/release references.
12. Every route-owned block appears in exactly one route release partition.
13. Same-direction route sharing is not represented as a conflict; independent conflicting routes are.
14. `git diff --check`, clean secret scan, commit-message/Change-Id preservation, Gerrit push, and remote refs read-back.

For YAML JSON Schemas with relative `$ref` values, avoid a relative `$id` that changes the resolution base unexpectedly. In Python tests, preload YAML library schemas as `referencing.Resource` entries in a `Registry`; independent `check-jsonschema` validation should be run with schema paths whose relative references resolve beside the root schema.
