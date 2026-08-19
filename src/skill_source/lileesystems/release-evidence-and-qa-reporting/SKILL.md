---
name: release-evidence-and-qa-reporting
description: Build presentation-ready release evidence and QA sections from authoritative test inventories, prior release baselines, and user-confirmed execution results without inventing cases or collapsing source granularity.
version: 1.5.0
author: Hermes Agent
license: MIT
---

# Release Evidence and QA Reporting

## Overview

Use this skill when a release note, release review, go/no-go brief, or launch page must explain **what changed, what was tested, and what remains uncovered** to a mixed audience of engineering, QA, partner teams, and non-technical stakeholders.

This skill complements product-specific authoring skills. Product-specific skills define the page family and source systems; this skill governs presentation, QA evidence integrity, and test-inventory reconciliation.

## Trigger Conditions

Load this skill when the task includes any of the following:

- a release-review document that will be used directly as presentation material,
- automated/manual/Uphill or equivalent QA sections,
- carry-forward of a prior release's complete automated inventory,
- marking test cases as new, passed, failed, blocked, or pending,
- selecting manual regression from a source test catalog,
- visual Before/After or scenario explanations for mixed technical audiences.

## Core Principles

1. **Source before summary.** Read the authoritative test inventory and prior published release before counting, selecting, or rewriting cases.
2. **Never invent a manual case to fill a coverage gap.** If the source catalog has no matching case, state the gap and add the case to the source catalog first.
3. **Preserve source case granularity.** A suite may contain multiple numbered cases, and each case may contain several route legs or steps. Do not collapse multiple numbered cases into one aggregate row or split one numbered case into invented subcases.
4. **Separate coverage layers by purpose.** Explain what targeted qualification, automated regression, and manual regression each cover; do not present only totals.
5. **Presentation content is not a ticket dump.** For mixed/non-technical release reviews, use scenarios, Before/After comparisons, metric cards, concise flows, and screenshots. Keep Jira traceability in planning/issue sections unless the user asks for it in the highlight section.
6. **Avoid duplication.** A test-automation improvement belongs in QA if repeating it in release highlights adds no audience value.
7. **Claims must match evidence.** Preserve user-confirmed execution results and distinguish measured validation from inferred improvement.
8. **User-provided visuals define the story sequence.** When the user adds or replaces screenshots, refresh the live artifact, preserve the media IDs and order, read the adjacent captions, and rebuild the narrative around that evidence. Remove any earlier prose or panels that tell a conflicting scenario; do not merely append the new visuals beneath the old interpretation.
9. **Traceability must be exhaustive without implying delivery.** When the user asks to show all release tickets, build a complete frozen cohort and place each ticket in exactly one intent-based group. Keep workflow status visible, and treat Study / Design / Discovery as traceability rather than a shipped-feature claim.
10. **Exhaustive means exhaustive within the approved audience boundary.** If the user intentionally removes internal enablement, team-management, hiring, or administrative work from an external release review, do not restore it merely to maximize ticket count. Recompute the retained cohort, group count, and summary immediately so the artifact does not claim coverage of deleted work.
11. **Keep visual-story semantics coherent across every layer.** When screenshots redefine a scenario, reconcile the section title, step labels, captions, nearby prose, spatial terminology, and any linked test/issue explanation. A technically true location statement may need both terms in one sentence rather than choosing one and creating a false contradiction. Do not carry a prior release's conceptual framing into the new release merely because the underlying issue family is related.
12. **Tell the product-release story, not the beta-build diary.** Release highlights normally explain previous GA behavior → current GA behavior. Intermediate beta builds, branch names, and patch sets are evidence provenance unless their identity is essential to the shipped behavior. When several investigations contribute to one outcome, merge them into one visible story—symptom → measured localization → corrective change → final release result—rather than creating a separate chapter for each internal issue/fix stage.
13. **Separate diagnosis from improvement.** A `How we located the bottleneck` visual must show only the state observed when the problem was discovered: input counts, stage counts, baseline latency, and the resulting localization. Do not mix fixed-state counts, After arrows, release semantics, or improvement percentages into those diagnostic rows. Put all correction and improvement evidence in a later `Before / After Validation` block.
14. **One visual row, one audience question.** A delivery/drop row answers where items disappeared; a latency row answers where time accumulated. Do not mix counts and timing across the same cards merely because both came from the same pipeline. Use concise, equal-width cards with one metric and one interpretation per card.
15. **Repeated metrics are a consistency contract.** If a latency appears in both a pipeline card and a summary table, the measurement boundary, percentile, harness, sample population, rounding, and Before/After values must match exactly. If a row comes from a different harness, label it visibly (for example `microbenchmark` or `controlled JPS`) instead of letting readers assume it belongs to the end-to-end pipeline.

## Required Source Stack

Read in this order:

1. Current live release artifact, preserving user edits.
2. Latest published prior release artifact for full inventory and visual baseline.
3. Authoritative test catalog for case IDs, names, setup, expected result, and automation status.
4. Current run reports or user-confirmed results.
5. Issue tracker only for traceability and scope checks, not as a substitute for test evidence.

Immediately before mutation, refresh the current live artifact and abort/rebuild if it drifted.

## Presentation Workflow

### 1. Identify the audience

If QA and non-technical attendees are present, design for both:

- non-technical readers need a scenario they can picture,
- QA needs coverage boundaries, inventory counts, new-case markers, and result status,
- engineers need traceability without implementation detail overwhelming the presentation.

### 2. Build release highlights as visual stories

Preferred patterns:

- `Before` versus `After` panels,
- a 3–4 step user/operator scenario,
- measured metric comparison table,
- validation metric cards,
- screenshot beside a concise scenario,
- explicit outcome/impact sentence.

Do not expose ticket IDs in the presentation section by default. Retain them in release-plan, known-issue, or traceability sections where appropriate.

When the user adds multiple screenshots to correct the release story:

1. Re-read the current live page rather than using the previous candidate.
2. Extract media IDs, column/order, captions, and nearby prose.
3. Treat the captions and the user's correction as the authoritative sequence.
4. Give each image one concise step label and one outcome-oriented caption.
5. Remove stale scenarios, Before/After panels, or issue-summary prose that conflict with the new image sequence.
6. Verify the persisted media IDs and order after write-back; preserving “three images” is insufficient if the order changed.

### 3. Visualize performance evidence by release question

Start with the release-level question: **what changed for the product from the previous release to the current release?** Do not let the order of internal beta builds become the chapter structure.

When several investigations contributed to one improvement, use a single evidence story:

1. user-visible symptom,
2. instrumentation across the relevant pipeline boundaries,
3. one-variable diagnostic that localizes the dominant gap,
4. production correction,
5. matched before/after proof,
6. complete-release acceptance gate.

Merge related runtime-hardening or follow-on validation metrics into the main before/after block when they explain the same release outcome. Do not leave a separate `stock X.YbN problem` mini-section merely because the raw evidence was collected in a later beta. Prefer visible labels such as `Previous release behavior`, `Before optimization`, and `SafeART X.Y`; retain exact beta/build provenance in linked RCA pages, evidence notes, or traceability.

Keep evidence questions and comparison boundaries explicit inside that story:

- **Matched diagnostic / controlled A/B:** fixed replay/input → before → after → compare the same measurement boundary. This supports localization or causal improvement claims within the matched pair.
- **Full-topology release validation:** current release build → complete stack → reproduced load → acceptance gates. This supports integrated release confidence.

These do not have to be separate top-level chapters. A timeline plus pipeline bottleneck map plus consolidated before/after tables can be clearer, provided each table compares only one matched harness/boundary. Put a visible interpretation rule near the metrics: values from different environments or boundaries must not be subtracted or ranked directly.

#### Diagnostic rows versus validation rows

When the document uses pipeline cards above a Before/After table, assign each region a single job:

1. **Problem-state delivery row:** show only baseline counts at each boundary. Make the loss location legible from left to right. A useful pattern is `input published` → `handler received` → `post-PubSub delivered` → `downstream observed`. If downstream can only see an already reduced stream, say so rather than implying it caused the loss.
2. **Problem-state latency row:** show only baseline latency at the same stage boundaries, normally one agreed percentile such as p99. Label each card with a short interpretation such as `handler fast`, `dominant controllable gap`, or `render fast`.
3. **Root-cause sentence:** localize the boundary using baseline evidence only. Do not prove the fix in the localization sentence.
4. **Before/After validation block:** show the improvement pairs, stall counts, release outcome, and any diagnostic one-variable proof. This is the sole visible home for After values when the user wants the diagnostic section to represent the original state.

Before publishing, build a metric identity key for every repeated number:

`boundary | start event | end event | percentile | harness | population | rounding`

Assert that each repeated card/table pair shares the same key and numeric values. Count occurrences in the governed section when practical. A label like `PubSub → GraphQL send` is too vague if the measured end is actually `graphql_before_yield`; use the instrumented boundary name and explain that it is not completed websocket flush.

Do not force every number to look improved. If an upstream p95/p99 is flat or worse because the fixed path retains more slow samples, show that honestly and describe the population change. The purpose of the pipeline is localization, not making every card green.

If an early beta merely carries forward previous-release behavior, describe it as previous-release behavior only when that equivalence is confirmed by the product owner or evidence. Otherwise use `Before optimization` rather than falsely relabeling the tested artifact. Do not claim that one fix caused a later issue unless the release note intentionally includes that causal RCA and authoritative evidence supports it.

Prefer native editable visual structures when the destination supports them. In Confluence ADF, remember that a `panel` cannot contain a `table`; for a card with metrics, place the panel header, table, and explanatory paragraph as sibling nodes inside a `layoutColumn`.

Every environment, workload, boundary, and acceptance count must come from an authoritative run report; do not invent missing methodology for visual completeness.

See `references/performance-evidence-visualization.md` for reusable layouts and the evidence checklist.

### 4. Add a QA coverage-at-a-glance section

Present three layers when applicable:

- **Targeted qualification / Uphill:** changed or newly introduced release behavior.
- **Automated regression:** broad, repeatable workflows and newly automated cases.
- **Manual regression:** long-duration, multi-vehicle, hardware/full-testbed, or human-observation scenarios unsuitable for automation.

For each layer show:

- passed/executed count,
- purpose,
- covered functional areas,
- notable exclusions or gaps.

A three-panel layout works well when the document format supports it.

## Release Ticket Traceability

Use this workflow when a release note or release-review artifact must show most or all tickets without becoming an unstructured issue dump.

1. **Freeze the cohort.** Query the complete release boundary (for example all named release sprints), then apply explicit inclusion/exclusion decisions. Do not use a `Done`-only query when the user wants full traceability.
2. **Classify by work intent, not merely issue type.** Useful class-level groups are:
   - Product / operational delivery,
   - Reliability / defect correction,
   - QA / E2E / testbed,
   - Study / design / discovery,
   - Platform / tooling / enablement.
3. **Make groups mutually exclusive.** A ticket belongs to exactly one group even if it has several labels. Define precedence rules before generating cards/tables.
4. **Keep Jira status visible.** The grouping explains why the ticket exists; Jira status explains whether it is Done, In Progress, Pending, or otherwise incomplete.
5. **Do not claim Study as delivery.** Research, UX diagnosis, architecture orientation, route-design baselines, and similar work can be release traceability while remaining non-feature outputs.
6. **Validate set arithmetic.** Assert:
   - union of groups equals the frozen retained cohort,
   - pairwise intersection is empty,
   - sum of group counts equals the unique total,
   - explicitly excluded IDs have zero occurrences in the full artifact, including explanatory prose.
7. **Use datasource tables or smart links in the traceability section, not the mixed-audience highlight section.**
8. **Honor intentional external-audience exclusions.** “Show all release tickets” does not override a later decision to remove internal/team-management work from an external review. Preserve the exclusion and recompute the retained union, per-group counts, group-number prose, and headline total in the same edit.
9. **Do not force dense Jira links into Plan/Actual summaries.** If the user removes those links for readability, keep the comparison at story/concept level and point readers to the dedicated traceability section instead.

## Targeted Qualification / Uphill Rules

1. Fetch the **latest live authoritative catalog** immediately before editing the release artifact. Test catalogs can gain cases while the release note is already under review; do not rely on an earlier exported inventory.
2. Preserve the source suite and case number exactly. Add S31.8, S31.9, and S32.2 as three rows—not an aggregate “speed-limit validation” row—and keep distinct create/update scenarios distinct.
3. Faithfully translate the source `Given` and `Expected Result`, including exact affected tracks, blocks, sub-blocks, or other configured units when the warning is unit-specific.
4. Make blocking semantics explicit. If validation is advisory, state both the warning content and that create/update remains allowed; do not let the word “validation” imply rejection.
5. A blank source result means **not yet evidenced**, not pass. Use a native `NOT RUN`/pending status until an authoritative run report or the user confirms execution. A later user confirmation may update the rows and rollups to `PASS`.
6. Synchronize all presentation layers in the same edit:
   - QA coverage-at-a-glance card,
   - targeted/Uphill section summary,
   - detailed case table.
   Derive counts from detailed rows and status nodes; do not leave a stale `4 / 4 PASS` card above a seven-row table.
7. If a source row contains an obvious copied-field contradiction (for example, `Given` says TSR while one phrase in `Expected Result` says another bulletin type), do not silently publish the contradiction. Preserve the uncontested tested behavior and omit or clarify the conflicting copied field; ask the owner if the conflict changes the acceptance claim.
8. Preserve execution provenance separately from case-definition provenance: record which catalog version defined the cases and who/what confirmed the run result.

## Automated Inventory Rules

1. Start from the complete automated table in the prior published release.
2. Remove stale `NEW` markers from prior-release additions. Check both native ADF `status` nodes and legacy plain-text suffixes such as `Vehicle Display new`; counting only status nodes can leave contradictory old labels visible.
3. Add every newly automated source case as its own row.
4. Mark only current-release additions as `NEW`.
5. Preserve `PASS`/`FAIL` status controls per row.
6. Reconcile totals from actual rows, not prose.
7. Verify:
   - total rows,
   - pass/fail counts,
   - current-release `NEW` count,
   - suite/category subtotal sum.
8. Do not include cases whose authoritative automation field still says `No`, `manual`, or `pending automation`.

## Manual Regression Rules

1. Select only cases that already exist in the authoritative catalog.
2. Require the source case to be explicitly manual/non-automated unless the user gives another rationale.
3. Prefer release-relevant cases that cover:
   - long-running behavior,
   - concurrency/multiple vehicles,
   - recovery after infrastructure restart,
   - physical/full-testbed behavior,
   - user-visible flows that automation cannot judge reliably.
4. Copy or faithfully translate the source `Given` and `Expected Result`; do not synthesize a new scenario.
5. Preserve case numbering exactly.
6. When the user confirms execution results, update every corresponding row and all roll-up counts.
7. If one source suite has cases 1–4, list cases 1–4 separately. If case 1 contains steps a1–d1, keep those steps inside case 1 rather than counting four cases.
8. If no catalog case covers a release risk, add a visible coverage-gap note instead of inventing a row.

## Count Reconciliation

Before publication, derive all rollups from table rows:

- `executed = pass + fail + blocked + other executed statuses`,
- `selected = number of data rows`,
- `new = rows marked current-release NEW`,
- coverage category subtotals must sum to the automated total,
- overview panel totals must match detailed tables.

Treat any mismatch as a blocker.

## Live-Edit Preservation

When the user may be editing the page concurrently:

1. Read the latest live artifact.
2. Diff against the prior snapshot.
3. Preserve user changes outside the requested section exactly.
4. Preserve user-updated result statuses inside the section unless the new instruction supersedes them.
5. Patch only the intended section.
6. Re-fetch immediately before write; abort on semantic drift.
7. Read back after write and verify the persisted table rows and rollups.
8. If version history shows the correct update but the user still sees older content, diagnose before republishing: inspect current ADF, rendered view, storage representation, current version, and server-side draft state. If all current server representations contain the new content and no draft exists, treat the discrepancy as a stale browser/editor client state. Tell the user not to publish from the stale editor; close/reopen or hard-refresh first. Do not create a redundant version just to invalidate client cache.
9. If the live baseline already fails a global document guard outside the governed section, compare baseline and candidate violation paths/attributes, prove they are unchanged, and run the guard on a temporary ADF document containing the complete governed scope. Require the scope to pass and report inherited global violations separately; do not expand scope merely to make the global guard green.

## Verification Checklist

- Presentation highlights contain no unwanted ticket cards.
- User-provided visual sequences preserve media IDs, order, captions, and the corrected scenario; conflicting old narrative is absent.
- QA overview explains purpose and scope, not only totals.
- Automated table carries the full prior inventory.
- Only current-release automated additions are marked `NEW`.
- Manual rows all originate in the source catalog.
- Source case numbering and route/step grouping are preserved.
- User-confirmed results are reflected in rows and rollups.
- Coverage gaps are explicit.
- Traceability groups are mutually exclusive and collectively exhaustive for the frozen retained cohort.
- Study/incomplete tickets retain visible status and are not described as delivered features.
- Explicitly excluded ticket IDs have zero occurrences across the full artifact, including prose.
- Non-targeted live content is unchanged.
- Persisted read-back matches semantically after renderer-only normalization.

## Common Failure Modes

- Summarizing automated coverage without listing the complete baseline inventory when the established release-note format expects the full table.
- Inventing manual regression cases because they seem release-relevant.
- Treating route legs such as a1–d1 as four cases when the source defines them as one numbered case.
- Collapsing source cases 1–4 into one aggregate row.
- Leaving stale `NEW` markers from the prior release.
- Showing ticket IDs and implementation prose to non-technical release-review attendees.
- Repeating a QA-only automation achievement in release highlights without additional audience value.
- Reporting a roll-up count that disagrees with table rows.
- Overwriting statuses the user changed in the live page.
- Appending a user-provided screenshot sequence while leaving an older, contradictory scenario above it.
- Preserving the right images but changing their order or detaching captions from the corresponding image.
- Using a `Done`-only query when the user asked for all release tickets.
- Grouping tickets by issue type alone, producing an unhelpful Epic/Story/Task dump.
- Letting one ticket appear in multiple traceability groups or failing to reconcile group totals against the frozen cohort.
- Treating Study, Design, or Discovery tickets as shipped features merely because they are in a release sprint.
- Mentioning explicitly excluded ticket IDs in an “excluded items” note, thereby violating a whole-artifact zero-occurrence requirement.
- Counting a repeated status label across the whole page when the assertion belongs to one section. Scope `NEW`, `PASS`, and similar roll-up checks to QA or the governed subsection; Known Issues or other sections may legitimately use the same status label.
- Treating a post-write assertion failure as proof that the Confluence mutation failed. If the PUT returned success, fetch the live version before retrying; repair the verifier and verify the persisted page instead of issuing a duplicate write.
- Preserving an intentional group deletion while leaving stale headline totals or “five groups” prose above the remaining four groups.
- Structuring a performance highlight around internal beta chronology (`stock bN`, `candidate`, later beta) instead of the audience-relevant previous-release → current-release change.
- Leaving a related runtime-hardening result in a separate mini-chapter when it should be merged into the main before/after product story.
- Nesting a Confluence ADF table inside a panel. Panels cannot contain tables; use sibling `panel` → `table` → explanation nodes inside the same layout column.
- Mixing fixed-state counts or Before→After arrows into a `How We Located the Bottleneck` row that is meant to represent the original problem state. Keep diagnosis baseline-only and move improvement to the validation block.
- Showing the same metric in a pipeline card and summary table with different boundary names, percentiles, rounding, or values. Treat repeated metrics as an assertion, not copy-edited prose.
- Putting packet-delivery counts and latency comparisons in the same visual row. Give each row one question and one interpretation path.

## Supporting References

- See `references/performance-evidence-visualization.md` for the product-release narrative, investigation-to-release layout, optional two-lane pattern, Confluence ADF nesting rule, and evidence-integrity checklist.
- See `references/performance-pipeline-diagnosis-validation.md` for the baseline-only localization pattern, metric identity contract, human-readable card design, population caveats, and candidate/read-back assertions.
- See `references/safeart-021-qa-review-lessons.md` for a concrete reconciliation example: 99-case automated inventory, three-layer QA overview, and preservation of four distinct S21 cases.
- See `references/safeart-021-uphill-speed-limit-cases.md` for a source-backed example of adding late catalog cases, preserving non-blocking warning semantics, reconciling 7/7 rollups, and separating case-definition provenance from user-confirmed execution results.
