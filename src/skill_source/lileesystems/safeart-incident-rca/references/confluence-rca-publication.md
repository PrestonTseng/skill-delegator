# Confluence RCA Publication Workflow

Use this when a SafeART RCA report must be created from a supplied template and placed beside existing reports.

## Discover the authoritative structure

1. Read the supplied template in ADF.
2. Record its numeric page ID, `parentId`, and `spaceId`.
3. Enumerate the template parent's depth-1 descendants.
4. Read two or three recent/relevant sibling RCA reports in ADF.

The template defines required sections. Siblings define current title style, evidence density, Jira-link placement, and useful appendices. "Same level" means the new page uses the template's exact `parentId`; the template itself is not the parent.

## Create Jira first

Create or identify the root-cause Bug before the page so its final key is available.

- Read Bug metadata before creation; do not guess required custom fields or allowed values.
- Read the Bug back and verify type, priority, severity, reproducibility, environment/build, status, and assignee state.
- Keep defensive mitigations as separate Tasks when they do not repair the root defect.
- Link Bug and Task with the appropriate Jira relationship, normally `Relates` unless stronger direction is proven.

## ADF page skeleton

Use this order unless the live template/sibling convention explicitly differs:

1. TOC extension as the first top-level node.
2. `Reported by ...` provenance when supported.
3. `Bug Ticket ` plus Jira `inlineCard`.
4. `TL;DR`.
5. `Issue`.
6. `Video`.
7. `Root Cause Analysis` with numbered evidence steps.
8. `Current Root Cause Statement`.
9. `Reproduce / Validation Steps`.
10. `Repair Suggestions`.
11. Optional `Evidence Appendix` in an expand node.

If no video exists, say so and name the evidence sources. Do not leave an empty section or invent media.

Prefer a standalone title:

```text
<BUG-KEY> <component and observable failure>
```

Use inline Jira smart links, not adjacent repeated ticket titles. Link defensive Tasks in the repair section and explain that they reduce impact rather than repair the root defect.

## Evidence writing

Show the investigation path:

1. establish comparable baseline/incident measurements;
2. map releases to exact component revisions;
3. check whether the failing endpoint changed;
4. isolate changed shared-runtime surfaces;
5. map production errors to exact source-created tasks/coroutines;
6. compare dependency/library changes;
7. record excluded candidates and evidence boundaries;
8. define one-variable A/B validation and acceptance thresholds.

Label direct findings as proven, source-isolated mechanisms as high confidence, and unprofiled causal shares as not quantified.

## Validate and publish

Save the draft ADF in the task plan directory and run:

```bash
python scripts/confluence_adf_guard.py validate page.json \
  --require-toc-first \
  --forbid-plain-links
```

Confirm:

- TOC first;
- no plain links under strict policy;
- Bug/Task links are `inlineCard` nodes;
- no invented `localId`, media ID, collection ID, or resource ID;
- no unsupported centered layout.

Create the page with the template's `spaceId` and exact `parentId`.

## Read-back verification

1. Read the created page in ADF.
2. Verify title, `spaceId`, exact template `parentId`, and `current` status.
3. Verify TOC remains the first node after Confluence round-trip.
4. Verify Bug and related-task smart-link URLs persisted.
5. Verify all required headings persisted.
6. Re-enumerate the parent depth-1 descendants and confirm the page is a sibling of the template.
7. Read the Jira Bug and verify the mitigation relationship persisted.
8. Report width as unverified unless a separate property-capable path set and read it.

## Pitfalls

- Copying only the template and missing current sibling conventions.
- Creating the page before the Bug and requiring an avoidable second edit.
- Making the template page the parent instead of using its parent.
- Conflating a bounded/idempotent caller mitigation with the server-side root repair.
- Claiming an exact CPU/event-loop contribution without profiling or controlled A/B.
