---
name: modeling-railway-trackwork-topology
description: Use when interpreting, designing, validating, or documenting railway track graphs involving turnouts, crossings, slips, multi-legged nodes, permitted train paths, route conflicts, or topology-to-physical-track correspondence.
---

# Modeling Railway Trackwork Topology

## Overview

A railway node's graph degree says how many track legs meet, not which legs a vehicle can physically traverse between. Model special trackwork as **ports plus permitted transitions**, grounded in switch/crossing geometry and interlocking behavior.

## Core Model

For each physical trackwork element record:

1. Stable port IDs and physical side/orientation.
2. `trackwork_type` (ordinary turnout, three-way turnout, diamond, single slip, double slip, etc.).
3. Undirected physical route pairs, or directed transitions if operating direction matters.
4. Point-position requirements for each transition.
5. Mutually conflicting routes and flank/clearance constraints.
6. Whether a requested destination requires reversal rather than a direct movement.

Never infer a complete graph from node degree alone.

## Quick Reference

For four ports split geometrically into left `{A,B}` and right `{C,D}`:

| Element | Direct undirected route pairs | Count |
|---|---|---:|
| Diamond crossing | `A-D`, `B-C` | 2 |
| Single slip | diamond pairs plus exactly one of `A-C` or `B-D` | 3 |
| Double slip | `A-C`, `A-D`, `B-C`, `B-D` | 4 |
| Arbitrary complete four-port node | every pair, including `A-B` and `C-D` | 6 |

A three-way turnout also has four ports, but one is the common stem `S`; only `S-X`, `S-Y`, and `S-Z` are direct. The three branches are not directly pairwise connected through the unit.

Directed counts are twice the undirected counts when movements are physically reversible: single slip 6, double slip 8.

## Identification Workflow

1. Label every incident leg before naming the element.
2. Identify which legs lie on the same physical side and which are continuations through the crossing.
3. Write the candidate route-pair set explicitly.
4. Compare that set with the quick-reference patterns.
5. Check official railway definitions or infrastructure schemas; prefer route wording over colloquial names.
6. If all six pairs are requested, test whether the drawing has collapsed several turnouts into one logical node. Expand it into multiple physical elements unless evidence supports bespoke special trackwork.
7. Report uncertainty when the diagram omits switch blades, frogs, point positions, or route indications.

## Source Discipline

Prefer railway infrastructure owners, regulators, accident-investigation bodies, and primary standards/schema maintainers. Cite direct document URLs and quote the route-defining sentence when possible. Do not rely on graph terminology or vendor marketing to establish physical connectivity.

For vetted definitions, route counts, and source URLs, read `references/four-leg-trackwork.md`.

When selecting an open-source infrastructure editor, canonical source format, or conversion workflow, read `references/open-source-infrastructure-authoring.md`. It compares OSRD/RailJSON, railML/RailTopoModel, JOSM/OpenRailwayMap, and SUMO, including licensing and semantic-fit pitfalls.

## Output Contract

For diagram reviews, give:

- a short verdict;
- a labeled port map;
- a table of permitted route pairs by candidate element;
- the distinction between direct movement and movement requiring reversal;
- primary/official citations;
- a recommendation to store an allowed-transition matrix rather than degree alone.

Match the user's requested language and concision. If they ask for concise Traditional Chinese, use short technical terms, preserve English railway terms in parentheses where useful, and avoid unrelated operational background.

## Common Mistakes

- Calling every degree-four node a four-way switch.
- Treating a diamond crossing as permitting a change between tracks.
- Treating a double slip as `K4`; it omits same-side direct exits.
- Confusing three-way turnout (one common stem, three branches) with a four-port crossing.
- Counting directed movements in one row and undirected route pairs in another.
- Assuming a schematic vertex is one physical appliance; it may abbreviate a ladder of turnouts.
- Citing a definition that names the appliance but does not establish its permitted routes.