# Four-Leg Railway Trackwork: Route-Pair Reference

## Normalized port convention

For a crossing-like drawing, place `A,B` on one physical side and `C,D` on the opposite side. Adjust the letters to the actual geometry before applying the table.

| Type | Direct undirected pairs | Directed movement count |
|---|---|---:|
| Diamond crossing | two track continuations only, e.g. `A-D`, `B-C` | 4 |
| Single slip | diamond pairs + one cross-connection, `A-C` or `B-D` | 6 |
| Double slip | all opposite-side pairs: `A-C`, `A-D`, `B-C`, `B-D` | 8 |
| Three-way turnout | common stem `S` to each branch: `S-X`, `S-Y`, `S-Z` | 6 |
| Complete four-port relation (`K4`) | all six unordered pairs | 12 |

A double slip is not `K4`: the two same-side pairs are not direct. railML explicitly says the third possible exit requires changing track and then reversing.

## Primary and official sources

### Transport for NSW — Glossary of Signalling Terms (TS 01296:1.0, 2022)

URL: https://standards.transport.nsw.gov.au/_entity/annotation/b2ff3f7a-49b8-f011-bbd2-7ced8da1764e

Relevant definitions:

- **Turnout:** assembly of stockrails, point switches, crossings, and closure rails by which rolling stock may be diverted from one track to another.
- **Diamond crossing:** one track crosses another; formed from two V crossings and two K crossings.
- **Single slip:** crossing plus one connecting track within the crossing limits.
- **Double slip:** crossing plus two connecting tracks within the crossing limits.

### UK Rail Accident Investigation Branch — Lewisham report 04/2018

URL: https://assets.publishing.service.gov.uk/media/5a968175e5274a5b849d3bbf/180228_R042018_Lewisham.pdf

Defines a diamond crossing as allowing two tracks to intersect at an angle **without enabling trains to change from one track to another**.

### UK Rail Accident Investigation Branch — Ealing Broadway report 24/2016

URL: https://assets.publishing.service.gov.uk/media/5a80007740f0b62305b8893f/R242016_161206_Ealing_Broadway.pdf

Defines a single slip as a diamond crossing of two lines with a connection between them in a single direction via two sets of points.

### UK Rail Accident Investigation Branch — Waterloo urgent safety advice 02/2017

URL: https://assets.publishing.service.gov.uk/media/5a81e22fed915d74e3400927/IR022017_171220_Waterloo.pdf

Defines a double slip as a crossover with four sets of switch rails, allowing two lines to cross with routes from each approach to each exit.

### railML 3 infrastructure/interlocking schema documentation

URLs:

- https://wiki3.railml.org/wiki/IS:switchIS
- https://wiki3.railml.org/wiki/Dev:Movable_Elements

Route semantics:

- `singleSwitchCrossing`: six directed movements, hence three reversible route pairs.
- `doubleSwitchCrossing`: eight directed movements, hence four reversible route pairs.
- A train entering a double slip may directly leave by either of the two tracks on the opposite side. Reaching the third exit requires a slip move followed by reversal.

This is the clearest source for distinguishing physical route pairs from graph degree.

### UK Ministry of Defence — Permanent Way Design and Maintenance, Issue 5

URL: https://assets.publishing.service.gov.uk/media/606444888fa8f515b28f4c53/MOD_UK_Rly_PW_DM_-_issue_5_final_v3.pdf

Section 2.10.2 defines a diamond as a same-grade crossing without track-to-track switching, and notes that layouts may instead use back-to-back turnouts. This supports expanding an over-compressed graph node into multiple physical units when needed.

### Primary geometry research on turnout types

URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC7472250/

Identifies three-way turnouts as a turnout class and describes an English double slip as two diverted connections built inside a diamond crossing. Use as supplementary primary research, not as the sole authority for operating route semantics.

## Modeling cautions

- Route-pair counts above describe **direct physical traversal**, not all destinations reachable after stopping and reversing.
- A schematic vertex may collapse multiple point machines or multiple turnouts.
- The handedness of a single slip determines which one of the two optional cross-connections exists.
- Directional signaling may further restrict a physically reversible pair; store operational direction separately from physical connectivity.
