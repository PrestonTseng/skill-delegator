# Topology data intake and collapsed trackwork

Use this reference when an engineer supplies the first site topology dataset after a railML-aligned schema has been approved, especially when the dataset compresses several physical turnouts into one schematic junction.

## Review sequence

1. Pin the current schema commit and the exact railML 3.3-SR2 XSD revision.
2. Parse the supplied inventory and report counts for vertices, sub-blocks, blocks/TVDs, signals, stopping places, direction locks, and switches.
3. Run semantic checks before proposing schema changes:
   - every reference resolves;
   - every point location lies within the referenced sub-block's positioning range;
   - units use one positioning system;
   - each sub-block has track ownership and navigability;
   - each ordinary turnout has three distinct incident legs;
   - graph degree greater than three is never assumed to be one switch or all-to-all connectivity.
4. Separate mechanical normalization from real contract changes. Renaming fields or adding document wrappers is not evidence that the schema is wrong.
5. Keep routes blocked until physical topology and switch-leg roles are approved.

## Unit and point-location trap

Do not normalize a short milepost such as `1139` by blindly multiplying it to match endpoint values such as `11300..11503`. Historical engineering points may contain meaningful final digits (`11398`, `10251`, `10254`, etc.). Ask for the authoritative metre value when the scale or precision is ambiguous.

A stopping place is normally a point (`sub_block_ref + milepost_m`), not a reason to split a physical edge. Removing stop-only vertices and replacing them with point locations is acceptable when connectivity is unchanged.

## Required-but-unresolved engineering data

For safety-significant static fields such as TVD boundaries and detection technology:

- keep the keys present so the data shape does not hide missing attributes;
- permit explicit `null # TODO(Preston): <specific question>` during engineering review when the schema profile allows it;
- reject deployable railML/ST generation while required profile facts remain null;
- never fabricate `virtual` boundaries, `simulated` detection, or empty lists to satisfy validation.

This distinguishes valid railML omission of an optional XML attribute from TAPAS profile completeness needed for a deployable simulator artifact.

## Collapsed turnout ladder pattern

A tree of three ordinary turnouts has five external legs and two internal connector edges. If a schematic uses one degree-five vertex and then puts switch IDs in `tip_sub_block_ref` or branch fields, the graph has collapsed physical topology.

Correct it by authoring:

- three distinct physical switch-point vertices;
- two connector sub-blocks between the switches;
- one ordinary turnout record per switch, with three sub-block references;
- reviewed track, block/TVD membership, extent/mileposts, and navigability for each connector.

Conceptual shape:

```text
A ----\
       SW1 -- INTERNAL-1 -- SW2 -- INTERNAL-2 -- SW3 -- D
B ----/                       |                    \
                              C                     E
```

Do not add `connected_switch_ref`, allow switch IDs in sub-block fields, place all switches on one vertex, or invent zero-length connectors. Those shortcuts lose the `NetElement`/`NetRelation` truth needed for deterministic railML conversion.

Before accepting the expansion, confirm:

1. physical switch order;
2. tip/left/right roles as viewed from switch begin/application direction;
3. distinct switch vertices and connector positioning extents;
4. connector track and TVD membership;
5. whether the equipment is truly ordinary turnouts rather than a slip or switch-crossing assembly.

## railML projection

For an expanded ordinary-turnout ladder:

- each sub-block becomes a `NetElement`;
- each allowed tip-to-branch traversal becomes a `NetRelation` with endpoint positions and navigability;
- each physical turnout becomes `SwitchIS`, whose branches reference those relations;
- each interlocking turnout becomes `SwitchIL` with `branchTip`, `branchLeft`, and `branchRight`;
- route position requirements use railML `left|right`; hardware `normal|reverse` remains adapter-only.

Relevant SR2 XSD areas:

- `rtm4railml3.xsd`: `RTM_Relation`, `RTM_SpotLocation`;
- `infrastructure3.xsd`: `StoppingPlace`, `SwitchCrossingBranch`, `SwitchIS`;
- `interlocking3.xsd`: `tSwitchPosition`, `SwitchIL`, `TvdSection`.

## Other high-degree junctions

After finding one collapsed junction, scan every degree-four-or-higher vertex. Classify each using physical evidence as an ordinary-turnout ladder, fixed diamond, slip/switch crossing, or data error. Never infer the appliance type or allowed transition matrix from degree alone.
