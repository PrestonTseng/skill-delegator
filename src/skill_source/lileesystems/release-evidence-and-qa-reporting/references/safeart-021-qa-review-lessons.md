# SafeART 0.21 QA Review Lessons

This reference records concrete evidence and corrections from the SafeART 0.21 release-note review. It is an example for the class-level workflow in `release-evidence-and-qa-reporting`, not a permanent baseline for later releases.

## Source anchors

- SafeART 0.21 Release Note: Confluence page `3878256653`
- Prior published baseline used for the complete automated inventory: SafeART 0.20 page `3806560282`
- Uphill Test Cases source: page `3524067749`, artifact version 49 during review

Always discover the latest live pages again for later releases.

## Presentation corrections

The release-review audience included QA, other teams, and non-technical attendees. The approved direction was:

- remove Jira ticket cards from the presentation-oriented Release Notes section,
- explain features with visual Before/After panels, operator scenarios, metric cards, and screenshots,
- remove the TSR Form E2E highlight because detailed automation evidence already appeared in QA,
- keep implementation traceability in plan/issue sections rather than release highlights.

## QA coverage overview

The three-layer summary used in the reviewed draft was:

- **Uphill — 4/4 PASS:** targeted route-authorization ownership and descending-milepost overlap boundaries.
- **Automated — 99/99 PASS:** broad repeatable regression.
- **Manual — 6/6 PASS:** long-running Mode-A and Manual-Manual route movement.

Automated category subtotals:

- Timetable / approval: 25
- Realtime display: 6
- TSV Visualizer: 11
- Manual Mode: 24
- Severity / DOM: 7
- Vehicle / User Management: 13
- TSR Form: 13 new in 0.21

Subtotal check: `25 + 6 + 11 + 24 + 7 + 13 + 13 = 99`.

The 99 automated rows consisted of 86 carried forward from 0.20 plus 13 new S31–S34 rows. Prior-release `NEW` markers were cleared; only the 13 current-release additions remained marked `NEW`. S34.2.1 and S34.2.2 were excluded from the automated table because Uphill marked them `No, 待自動化`.

## Manual source reconciliation

The final manual table contained six existing Uphill cases, all user-confirmed PASS:

- S10.1 — Mode-A 0101U long-run observation
- S10.2 — Mode-A services 118–120 with three vehicles
- S21.1
- S21.2
- S21.3
- S21.4

S11.9 was removed by user instruction.

### S21 source granularity

Uphill defined S21 as four numbered cases. Each case contains a route sequence with four labeled legs. Preserve the numbered cases; do not collapse cases 1–4 into one row, and do not count each leg as a separate case.

- **S21.1:** `(a1) AV1 → N2W-N; (b1) N2W-N → S2W-N; (c1) S2W-N → N2W-S; (d1) N2W-S → AV1`
- **S21.2:** `(a2) AV1 → N2W-S; (b2) N2W-S → S2W-S; (c2) S2W-S → N2W-N; (d2) N2W-N → AV1`
- **S21.3:** `(a1) AV1 → N2W-N; (b3) N2W-N → S2W-S; (c3) S2W-S → N2W-S; (d1) N2W-S → AV1`
- **S21.4:** `(a2) AV1 → N2W-S; (b4) N2W-S → S2W-N; (c4) S2W-N → N2W-N; (d2) N2W-N → AV1`

Shared source behavior:

- Given: create a no-service timetable, create a V1 service, and dispatch V1.
- Expected: the vehicle completes the selected SG according to the defined route and timing.
- Automation status: manual/non-automated because long observation is required.

## Coverage-gap handling

The source catalog did not contain an existing non-automated TSR max-speed-warning case. The correct response was a visible coverage-gap note, not an agent-generated manual test case. If that risk requires manual release coverage, add the case to Uphill first and then cite it in the release note.

## ADF read-back normalization observed

Confluence persistence may add renderer-only metadata while leaving semantic content intact. The comparator needed to ignore:

- generated `localId` and macro IDs,
- TOC macro `_parentId`,
- media `__fileName`, `__fileMimeType`, and `__fileSize`,
- integral float/integer differences,
- empty attrs/text nodes and adjacent equivalent text-node merging,
- Confluence smart-link title-slug differences for the same page ID.

Do not ignore real text, marks, node types, media ID/collection, target page IDs, table rows, or status changes.

## Three-image story correction

A later review correction showed why screenshot sequence must outrank an agent's earlier interpretation.

The initial prose framed the route-authorization problem as a trailing train mistakenly reusing authorization from a preceding train. Preston then added three images and captions that established a different sequence:

1. V2 already has H2T route authorization and is ready to proceed.
2. A temporary foreign-object event in C2T is cleared and consumes C2T authorization; V2 reaches signal 2R without authorization and stops.
3. Before 0.21, V2 remains stopped until mission timeout. In 0.21, SS detects the abnormal C2T authorization state, requests authorization again, clears 2R green, and lets V2 continue.

The correct edit was not to append the images beneath the old scenario. It was to refresh the latest live ADF, preserve the three media IDs and order, replace captions with concise Step 1/2/3 labels, and remove the contradictory old narrative and panel entirely.

Verification checked:

- exactly three persisted media nodes,
- media IDs in the same order as the user's live edit,
- all Step 1/2/3 labels present,
- the old scenario phrase absent,
- content outside the two governed sections unchanged.

## Ticket traceability correction

The initial 2.7 section used a `Done`-only delivery query plus small reliability and E2E subsets. That did not satisfy “show as many release tickets as possible with logical classification.”

The corrected workflow queried all tickets assigned to the three SafeART 0.21 sprints, applied the standing exclusions, and froze 67 retained tickets. They were placed into five mutually exclusive groups:

- TSR / Bulletin & Product Delivery: 16
- Reliability & Bug Fixes: 20
- QA / E2E / Testbed: 7
- Study / Design / Discovery: 16
- Platform / Tooling / Team Enablement: 8

Set verification required:

- `16 + 20 + 7 + 16 + 8 = 67`,
- 67 unique IDs,
- zero cross-group duplicates,
- every frozen retained ticket present,
- excluded IDs absent from the entire ADF, including explanatory text.

`Study` covered explicit study/orientation work, UX research, user interviews, WSS redesign baselines, and design/semantic clarification. Jira Status remained visible in every datasource table, so inclusion in release traceability did not imply that Study, In Progress, or Pending work was delivered.
