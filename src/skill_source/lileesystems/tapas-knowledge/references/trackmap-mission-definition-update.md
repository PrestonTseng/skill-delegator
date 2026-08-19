# TrackMap / Mission Definition Update — vertex / block / sub_block semantics

Use this note when discussing Thalos TrackMap/Mission data-model changes around TSR precision, AV1/AV2 handling, parking, and charging.

## Backlog context
From Confluence page `Backlog - TrackMap/Mission Definition Update`:
- item 1 needs clearer Line / Track semantics so Dispatcher can configure TSR precisely.
- item 2 needs JPS to treat yard-side locations as schedulable operational resources instead of assuming everything after arrival at AV1/AV2 is outside schedule scope.

## Current code semantics
### `vertex`
Topology anchor only.
- fields: `id`, `milepost`, `name`, `is_platform`, `is_yard`
- source: `thalos/model/track_map.py`

### `sub_block`
Smallest directed movement segment.
- fields: `id`, `name`, `block_id`, `from_vertex`, `to_vertex`
- source: `thalos/model/track_map.py`

### `block`
Movement-control aggregation of one or more sub-blocks.
- fields: `id`, `name`, `sub_block_list`
- source: `thalos/model/track_map.py`

## Runtime implications
- Movement-authority range is computed from `sub_block_list` (`ma_manager_service.set_range`, `_calc_milepost_range`).
- Mission control / nibble flow is driven by `mission.block_id_list`.
- `block` and `sub_block` already carry movement semantics; do not overload them with parking or charging resource semantics.

## Verified inventory snapshot
- vertices: 45 total
- named vertices: 8
- unnamed vertices: 37
- platform vertices: 8
- yard vertices: 2 (`AV1`, `AV2`)
- blocks: 28
- sub-blocks: 51
- signal `line_id` values present: `WT`, `ET`

## Important modeling smell
`AV1` and `AV2` are currently the only vertices that are both:
- `is_platform=True`
- `is_yard=True`

That means the model is already collapsing three roles into one point:
1. mission endpoint
2. yard handoff / interface
3. future parking / charging gateway

## Mission / trip constraints to remember
- `Mission` validation currently requires the first and last sub-block to touch a platform vertex.
- Charge trips currently stop at `AV1` / `AV2`; there is no separate parking-bay, charging-bay, release-timing, or capacity object yet.

## Vocabulary inconsistency to resolve before redesign
Current code mixes location vocabularies:
- bulletin lane enum: `AV`, `WT`, `ET`
- signal `line_id`: `WT`, `ET`
- ADS vehicle command / status examples: `NT`, `ST`

Do not let TSR UI, JPS scheduling, and SS consumption evolve on different location vocabularies.

## Recommended sequencing
1. unify line/lane semantics first
2. keep `vertex` / `sub_block` / `block` as topology + movement layer
3. add separate operational-node / operational-resource layer for parking / charging / release timing
4. relax mission endpoint assumptions so non-passenger operational nodes do not need to masquerade as platforms
5. only after that decide whether a finer yard-routing graph is necessary

## Strong recommendation
Use a two-layer model:
- Layer A: topology / movement (`vertex`, `sub_block`, `block`)
- Layer B: scheduling / resource (`OperationalNode`, `OperationalResource`, optional transfer edges)

## Railway grounding used in the review
These citations support separating movement-protection semantics from yard resource scheduling:
- GCOR 15.1: track bulletins cover conditions affecting safe train or engine movement.
- GCOR 15.2: a train must not enter limits unless instructed by the employee in charge.
- GCOR 1.46: the yardmaster is responsible for yard movement into and out of the yard.
- GCOR 7.1: equipment must not be left where it fouls adjacent tracks.
- GCOR 8.2: switches must not be lined away until equipment has passed the clearance point.
- 49 CFR §218.101: leaving equipment in the clear.
- 49 CFR §218.103: hand-operated switch responsibilities.
- 49 CFR §218.105: additional requirements for hand-operated main track switches.
- 49 CFR §218.99: shoving/pushing job-briefing and oversight requirements.

## Reusable meeting call
For cross-team discussion, recommend this call:
- do **not** redefine `block` / `sub_block` as parking or charging resources
- treat `AV1` / `AV2` as interface nodes, not the entire yard model
- model charging areas as independent capacity-1 resources from day one
- make vocabulary cleanup a prerequisite for both TSR precision and yard-resource scheduling
