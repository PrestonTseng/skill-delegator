---
name: safeart-release-note-authoring
description: Write or update SafeART release notes by discovering the latest published SafeART release note as the formatting baseline, asking for release-specific inputs, freezing the release bug cohort, and assembling QA sections from the previous release note plus the Uphill Test Cases page.
version: 1.1.0
author: Hermes Agent
license: MIT
---

# SafeART Release Note Authoring

## Overview

Use this skill when drafting, revising, or publishing a **SafeART release note**.

This is a **company-specific top-level skill**. It encodes the SafeART release-note structure, formatting discipline, and section-specific data-collection workflow.

**Important rule:** do **not** hardcode one historical release note as the permanent golden copy.
The agent must first discover the **latest published SafeART release note** and use that page as the formatting and structure baseline, so the workflow stays current as the document evolves over time.

Historical anchors that informed this skill:
- SafeART 0.20 Release Note page: `3806560282`
- SafeART 0.19 Release Note page: `3736535112`
- Uphill Test Cases page: `3524067749`
- Atlassian cloudId: `302f7dfa-a172-4986-b4ae-efd7021f110a`

Those page IDs are reference anchors, **not** a permanent instruction to always clone 0.20.

## When to Use

Use this skill when the user asks to:
- create a new SafeART release note,
- update an in-progress SafeART release note,
- rewrite one section of a release note while preserving the rest,
- generate a review draft before publishing to Confluence,
- collect release bugs / QA evidence into the SafeART release-note format.

Do **not** use this skill for:
- Jira ticket writing,
- general Confluence design docs,
- release-review spoken scripts.

## Non-Negotiable Rules

1. **Discover the latest published SafeART release note first.**
   - Do not assume 0.20 is still the newest baseline.
   - Use Confluence search to identify the newest relevant SafeART release-note page.
   - Use that newest page as the structural / formatting source of truth.

2. **Read the baseline page in ADF first.**
   - Treat it as the structural and formatting source of truth.
   - Do not rely on markdown alone for formatting decisions.

3. **Load `lilee-confluence-adf-authoring` before any Confluence mutation.**
   - Follow the ADF-first, surgical-patch workflow from that skill.

4. **Preserve the latest baseline page structure and formatting exactly unless the user explicitly asks to redesign it.**
   - TOC stays first.
   - Headings and numbering stay in the same style.
   - Existing media / tables stay untouched when the task is only to patch prose.

5. **Do not manually approximate table styling when ADF cloning is possible.**
   - Copy the exact table nodes or exact `attrs` / `colwidth` layout from the latest baseline page.
   - If exact widths matter, derive them from the live ADF you just read, not from memory.

6. **Never invent release facts.**
   - If version number, release time, bug cohort, QA counts, or test selection are missing, ask the user or retrieve the missing data from the source systems.

7. **Freeze the release note against live drift.**
   - Jira queries can change after publication.
   - Before publishing final counts, freeze the intended release cohort in the artifact or work files and verify the listed issues / rows match that frozen set.

8. **Reuse prior release-note wording when the same scenario already existed.**
   - Especially for QA rows, do not rewrite a good prior row just to sound fresh.

9. **Use Atlassian status controls for status-like cells in Confluence when feasible.**
   - Result / state cells such as pass, fail, open, resolved, approved, blocked should use ADF status nodes in authored or edited table regions unless the user explicitly wants plain text.

## Source Stack (read in this order)

1. **Current target release note page** in ADF if one already exists.
2. **Latest published SafeART release note** in ADF, discovered live from Confluence search.
3. **Previous release note relative to that baseline** for wording carry-forward.
4. **Release scope sources**:
   - current Jira issues,
   - release-planning / design pages,
   - task-plan notes under `/opt/data/plans/...` if the work is resumed.
5. **Uphill Test Cases** page for QA extraction.

## How to Discover the Baseline Release Note

Before drafting, search Confluence for SafeART release-note pages.

Preferred approach:
1. Search Confluence / Atlassian for pages whose title matches the SafeART release-note naming pattern.
2. Identify the newest published release note in the same family.
3. Read that page in ADF.
4. Use that page — not an older hardcoded example — as the formatting baseline.

If multiple candidate pages exist:
- prefer the highest actual release version,
- prefer the latest finalized / published release-note page over scratch drafts,
- if ambiguity remains, stop and ask the user which page should be treated as the baseline.

## Current Known Structure Pattern

The latest release note is expected to resemble this family pattern unless the newest baseline page proves otherwise:

- `1. Timeline`
- `2. Release`
  - `2.1. Deliverables from This Release`
    - `2.1.1. The Release Build`
    - `2.1.2. Documentation`
  - `2.2. Release Notes`
  - `2.3. Release Plan Before Kick-off`
  - `2.4. Known Issues`
    - `2.4.1. Resolved in This Release`
    - `2.4.2. Still Open`
  - `2.5. Quality Assurance`
    - `2.5.1. Uphill Testing`
    - `2.5.1.1. <feature-specific uphill subsection when needed>`
    - `2.5.2. Regression Testing`
    - `2.5.2.1. Automated E2E Testing`
    - `2.5.2.2. Manual Regression Testing`
  - `2.6. Release Meeting Recording and Minute`
  - `2.7. Epic / Story / Task`
- `Revision`

Treat this as a **known family pattern**, not as a substitute for reading the latest page.

## Formatting Guardrails

These are working expectations to preserve unless the live baseline page says otherwise:

- TOC is the first top-level node.
- Tables are left-aligned (`layout: align-start`).
- Tables are full width (`width: 1800` / `1800.0`).
- Known table families observed in recent SafeART release notes:
  - documentation: 4-column table,
  - known issues: 5-column tables,
  - QA: 7-column test-case tables,
  - revision: 3-column table.
- Link-style text in recent ADF snapshots uses Atlassian blue `#0747a6`.
- When exact column widths matter, clone the ADF node or copy the exact live `colwidth` arrays from the baseline page you just read.

**Do not hardcode widths from this skill when the live latest release note is available.**
This skill defines the method: discover latest baseline -> read ADF -> clone exact structure.

## Mandatory Workflow

### Step 1 — Gather anchors

Before drafting, determine:
- target release version,
- target release-note page,
- latest baseline release-note page,
- previous release-note page relative to that baseline,
- release scope / feature list,
- bug cohort source,
- QA source pages.

If any of these are not obvious, retrieve them before drafting.

### Step 2 — Build from the latest baseline, not from scratch

For a new release note:
- clone the latest baseline structure first,
- then replace only the release-specific content.

For an update to an existing page:
- read the target page in ADF,
- patch only the requested sections,
- preserve all non-targeted nodes exactly.

### Step 3 — Apply section-specific rules

#### 2.1. Deliverables from This Release

**You must ask the user for:**
- release version number,
- release date / time / schedule wording needed for the page.

Never invent those values.

Keep the baseline subsection structure:
- `2.1.1. The Release Build`
- `2.1.2. Documentation`

For documentation rows:
- keep the same table structure as the baseline page,
- keep wording concise and artifact-oriented,
- preserve link style and table formatting from the baseline page.

#### 2.2. Release Notes

This section is **content-flexible**.

Rules:
- there is **no fixed subsection schema** beyond matching the overall page style,
- the content should follow the actual release scope,
- feature subsections can expand or shrink based on what shipped,
- if an existing live subsection already contains tables / screenshots / media, preserve those nodes exactly and only complete the missing prose around them.

Preferred prose pattern:
- start with the release-level or feature-level framing,
- explain what materially changed,
- bound the claim so it does not overstate undelivered scope,
- close with operational / validation significance when useful.

#### 2.3. Release Plan Before Kick-off

Keep the baseline plan-vs-actual presentation style.
Do not turn this into a long narrative section.

#### 2.4. Known Issues

Use the **latest baseline structure**, not an outdated intermediate draft pattern.

If the latest baseline still uses the resolved/open split, preserve that split.
If the latest baseline evolves in the future, follow the latest baseline unless the user explicitly asks to keep an older structure.

For the currently known modern pattern, required subsections are:
- `2.4.1. Resolved in This Release`
- `2.4.2. Still Open`

Current known table columns:
1. `Priority`
2. `Scope`
3. `Duration`
4. `Summary`
5. `Resolution / Impact & Mitigation`

Required data workflow:
1. Use the same bug-harvest approach as the latest baseline release note.
2. Query all bug issues for the release cohort with JQL.
3. Verify whether sprint-only filtering misses intended release bugs.
4. Freeze the final intended cohort before publication.
5. Ensure the listed tickets, counts, and prose all match the frozen set exactly.

Authoring rules:
- `Summary` should include the inline Jira issue link and the issue summary.
- `Duration` should reflect the first release where the defect was known / relevant through the resolved release or `TBD`.
- Resolved rows should use direct release-resolution wording.
- Open rows should use the pattern:
  - `Impact: ...`
  - `Mitigation: ...`
- If no supported mitigation exists in Jira / source material, keep mitigation as `--` rather than inventing one.
- Preserve Preston's direct mitigation wording style.

#### 2.5. Quality Assurance

This section must combine:
- the **previous release note**,
- the **current Uphill Test Cases page**,
- **user-specified release boundaries**.

You must ask the user:
1. which uphill test cases are **new / updated** for this release,
2. which **manual** test items were executed for this release.

Then do all of the following:
1. Read the previous release note QA section first.
2. Copy prior row wording directly when the same scenario already existed.
3. Read the Uphill Test Cases page and inspect all relevant test cases.
4. Determine which automated cases are new and must be added.
5. Preserve any user-defined inclusion / exclusion rule for the release scope.
   - Example: if the user says Tools / Hydra are out of scope, exclude them.

Current known section shape:
- `2.5.1. Uphill Testing`
  - count line for `New / Updated Test Cases`
  - count line for `Passed`
  - optional feature-specific subheading like `2.5.1.1 ...`
  - optional prerequisite sentence before the table when setup is required
  - 7-column test table
- `2.5.2. Regression Testing`
  - total executed sentence
  - total passed line
  - classification note
  - `2.5.2.1. Automated E2E Testing`
    - count line
    - 7-column test table
  - `2.5.2.2. Manual Regression Testing`
    - count line
    - 7-column test table

Current known QA table columns:
1. `Test Suite`
2. `Suite Name`
3. `Case #`
4. `Summary`
5. `Given`
6. `Expected Result`
7. `Result`

QA wording rules:
- keep row wording short and test-case-like,
- keep `Given` as step-like setup text,
- keep `Expected Result` as verifiable system behavior,
- when a prior release already had an acceptable row for the same scenario, copy it instead of paraphrasing,
- for new cases from the Uphill page, simplify them into the same row style as the release note.

#### 2.6. Release Meeting Recording and Minute

Keep the section concise and artifact-link oriented.
Do not inflate it into narrative prose.

#### 2.7. Epic / Story / Task

Use Epic / Story / Task level traceability.
Do **not** narrate sub-task execution detail unless the user explicitly asks.

Group by delivered feature area when that matches the release story.

### Step 4 — Verification before publish

Before writing back to Confluence, verify:
- the page still matches the latest baseline structure,
- TOC is still first,
- non-targeted nodes are unchanged,
- table layouts / widths / column structures still match the intended baseline,
- issue counts match the frozen JQL cohort,
- QA counts match the selected rows,
- prior-row reuse happened where applicable,
- any new automated rows were actually sourced from the Uphill Test Cases page.

### Step 5 — Read back after publish

After write-back:
- re-read the page in ADF,
- confirm the intended headings exist,
- confirm key table nodes persisted,
- confirm status nodes / links / widths survived the round trip,
- report exactly what changed.

## Common Failure Modes

1. Drafting from memory instead of discovering and cloning the latest release-note ADF structure.
2. Treating 0.20 as a permanent golden copy after later release notes exist.
3. Rebuilding a table in markdown and losing the exact Confluence layout.
4. Inventing `2.1` version / time values.
5. Using live JQL counts without freezing the intended cohort.
6. Rewriting QA rows that should have been copied from the previous release note.
7. Forgetting to compare the Uphill Test Cases page against the previous release note to find newly automated cases.
8. Patching a live page without preserving existing screenshots / tables exactly.

## Final report requirements

When finishing a release-note task under this skill, explicitly state:
- target page title and page ID,
- which page was used as the latest baseline release note,
- whether this was a draft-only task or a Confluence write-back,
- which sections were changed,
- which inputs were user-provided,
- which Jira / Confluence sources were used,
- which bug JQL / frozen cohort was used,
- which QA rows were copied from the previous release note,
- which QA rows were newly added from the Uphill Test Cases page,
- whether ADF read-back verification passed.
