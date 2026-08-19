---
name: lilee-delivery-map-authoring
description: >
  Create Lilee feature-level Delivery Map drafts/pages using the standard format derived from
  the TSR Delivery Map: purpose + related-links + workstreams skeleton, release-ordered
  workstreams, assignable PD/FE/BE items, and explicit traceability to spec, ticket, owner,
  and due date.
version: 1.0.0
---

# Lilee Delivery Map Authoring

## Overview

Use this skill when Preston wants a **feature-level Delivery Map** for a new topic, or wants an existing delivery page reshaped to follow the standardized Lilee format.

A Delivery Map is the middle layer between:
- the **spec / backlog page** as behavioral source of truth, and
- the **KPI / release page** as lightweight release tracking.

The Delivery Map exists to show, for one feature across releases:
- what work exists,
- how that work is grouped into workstreams,
- which ticket tracks each concrete item,
- who owns it,
- when it targets delivery,
- and which exact spec section defines the expected behavior.

## When to use

Use this skill when the user asks to:
- create a new Delivery Map page,
- make a feature plan follow the TSR Delivery Map style,
- convert a backlog/spec into workstreams and assignable items,
- standardize a feature-tracking page so future topics can follow the same format.

Do **not** use this skill when:
- the artifact should be a release KPI page instead of a feature page,
- the artifact should be a behavioral spec,
- the user wants engineer-level implementation subtasks beyond assignable PD / FE / BE granularity.

## Non-negotiable framing

1. **Source of truth comes first.** Read the live spec/backlog page, related Jira tickets, and any cited design pages before drafting claims.
2. **The Delivery Map is not the behavioral golden copy.** It packages execution, scope, dependency, and ownership; detailed semantics stay in the source spec.
3. **No separate `Page Rules` section by default.** Bake the rules into the structure itself.
4. **Workstreams come first.** Split structure correctly before polishing wording.
5. **Workstreams are release-ordered.** Do not sort by abstract subsystem taxonomy unless the user explicitly asks.
6. **One workstream = one capability / function boundary.** Split more finely than epic-level buckets.
7. **Work items stop at assignable granularity.** Default lanes are PD, FE, and BE.
8. **Visible gaps are good.** If a ticket, owner, or due date does not exist yet, leave the gap visible instead of inventing one.
9. **Formal artifact language is English by default.** Chat with Preston can stay Chinese.

## Standard page shape

Unless Preston overrides it, a Delivery Map should use this top-level skeleton:

1. `# 1. Page Purpose`
2. `# 2. Related Links`
3. `# 3. Workstreams`

### 1. Page Purpose

State:
- what this page tracks,
- what a reader should be able to see quickly,
- and what remains out of scope because another page is the source of truth.

Keep it short and operational.

### 2. Related Links

Include only the links that help a reader navigate the execution package, typically:
- release KPI pages,
- the source spec/backlog page,
- epic / umbrella Jira ticket,
- major design documents when they shape a workstream.

Links should be hyperlinks in draft form, and smart links when published to Confluence.

### 3. Workstreams

Organize the page as numbered workstreams:
- `## 1. ...`
- `## 2. ...`
- `## 3. ...`

Do **not** label headings `Workstream 1`, `Workstream 2`, etc. Use the numbered form directly.

## Workstream format

Each workstream should follow this structure:

### Heading line

Format:

`## <N>. <Workstream title> <Target release status label(s)>`

Rules:
- The heading number is the canonical workstream order.
- Release targets belong in the heading as status-style labels, **not** as a table column.
- More than one release label is allowed when a workstream intentionally spans releases.
- When publishing to Confluence for Lilee delivery maps, render release labels as **purple** Atlassian status controls unless Preston explicitly asks for a different color.

### Subtitle

Immediately below the heading, add one compressed sentence in a consistent pattern.

Preferred pattern:
- `The system must ...`

This sentence defines the workstream goal in execution language, not low-level implementation language.

### Metadata blocks

Use these blocks in this order:

1. `**Scope boundary**`
2. `**Current Owner**`
3. `**Story Ticket**`
4. `**Design Document**` (optional)

Rules:
- `Scope boundary` should explicitly say what is in scope and, when useful, what is out of scope.
- `Current Owner` is enough by default; do not add separate handoff fields unless asked.
- `Story Ticket` should point to the umbrella ticket for the workstream when one exists.
- If no workstream-level ticket exists yet, leave the gap visible (for example blank or an explicit optional/not-created marker if the page style already uses it).
- Only add `Design Document` when a specific design page materially shapes that workstream.

## Work-item table format

Each workstream gets **one complete table** with these columns:

`Work Item | Function | Deliverable / Done When | Assignee | Ticket | Due Date | Spec Reference | Notes / Dependency`

Do not add or remove columns unless Preston explicitly asks.
When publishing live to Confluence, match the current Lilee Delivery Map table convention: use native ADF table attrs `layout: align-start` and `width: 1800` on each workstream table instead of the default narrow table width. For the Revision table, use `layout: align-start`, `width: 1800`, and column widths `Date=161`, `Description=1352`, `Author=285`. Verify the persisted ADF after save rather than assuming the editor kept the width.

### Column rules

#### Work Item
- Prefix each item with a stable ID like `[WS6.4]`.
- Numbering should nest under the workstream number.
- The text after the ID should be concrete enough to assign without further decomposition.

#### Function
- Prefer `PD`, `FE`, or `BE`.
- Use combined values like `FE / BE` only when the item genuinely stays shared at this planning level.

#### Deliverable / Done When
- Describe the reader-visible or execution-visible completion state.
- Write it as a concrete outcome, not a vague activity.

#### Assignee
- Use the current named owner when known.
- If unknown, leave it visible as a gap rather than guessing.
- In Confluence-published delivery maps, assignee cells should use native Confluence `mention` nodes, not plain text.

#### Ticket
- Every concrete work item should map to a Jira ticket when one exists.
- If no ticket exists yet, leave the cell empty so the gap is visible.

#### Due Date
- Use an explicit date when committed.
- If the schedule is dependency-derived and the page convention already uses formulas, a dependency expression is acceptable.
- Never invent dates.

#### Spec Reference
- If a source spec/design document exists, link back to it from the `Spec Reference` cell, as tightly as possible to the exact story/section rather than only the top of the spec page.
- If Confluence cannot deep-link the exact section reliably, use an inline smart link to the source spec page plus a short section/story label.
- If no source spec/design document exists, use a concise numbered item list in the cell to state the relevant spec points directly.
- If the linked source is too sparse to help a reviewer, and Preston wants the table itself to be actionable, put the exact work-item acceptance criteria directly in the `Spec Reference` cell instead of a weak link or vague story label.

#### Notes / Dependency
- Use this for carry-over context, dependency statements, constraints, or ticket-gap notes.
- Keep notes short and execution-relevant.

## Authoring workflow

1. **Read the live sources first.**
   - Spec/backlog page
   - Existing Delivery Map if one exists
   - Related KPI page if it constrains release framing
   - Jira tickets that anchor workstreams or work items
   - When the task is a due-date / release-label refresh rather than a structural rewrite, also follow `references/tsr-due-date-maintenance.md`.
   - When the task is a Mermaid Gantt chart from a Delivery Map, follow `references/delivery-map-gantt.md` and use `scripts/delivery_map_gantt.py` where possible.

2. **Decide the right workstream cut before wording cleanup.**
   - Split by capability boundary.
   - Order by release sequence.
   - Preserve already-committed historical workstreams as history when the page is evolving, instead of collapsing them away.
   - When the source spec is organized as repeated lifecycle stories per service/component (for example design document → implementation architecture design → implementation), default the Delivery Map workstream cut to one workstream per service/component and put the lifecycle stories as work items inside that workstream. Do not create separate cross-service workstreams for `Required Development Flow` or `Service Design Document Requirements` when those requirements are already folded into story acceptance criteria.
   - If no release target is present in the source, keep the release-label gap visible with a status such as `Target TBD` rather than inventing a SafeART release.

3. **Write the page skeleton.**
   - Page Purpose
   - Related Links
   - Workstreams section with numbered headings

4. **Draft each workstream top-down.**
   - heading with release label(s)
   - one-sentence subtitle
   - scope boundary
   - owner
   - story ticket
   - optional design document
   - one full table

5. **Normalize wording across the full page.**
   - consistent subtitle pattern
   - consistent scope-boundary phrasing
   - consistent terminology
   - concrete, assignable work-item names

6. **Check traceability.**
   Every workstream should make it easy to answer:
   - why this workstream exists,
   - what source story defines it,
   - which ticket tracks it,
   - who currently owns it,
   - which release it belongs to.

7. **If publishing to Confluence, convert the packaging correctly.**
   - release labels → purple Atlassian status controls by default for release identifiers
   - URLs / Jira links → smart links unless the user explicitly wants plain text in a field such as a sparse spec-reference column
   - assignee / current-owner people fields → native mentions
   - preserve the page skeleton and existing non-targeted content if editing live pages
   - delivery-map workstream tables intentionally use ADF `layout: align-start` with `width: 1800`; after write-back, run a custom read-back check to verify every workstream table persisted with those attrs.

8. **When refreshing due dates on an existing delivery map, treat the refresh as a calculation pass, not a rewrite.**
   - Use `scripts/delivery_map_due_refresh.py` where possible instead of hand-editing formula cells.
   - If Preston also asks to adjust Jira ticket basics, update Jira metadata from the Delivery Map source row in the same pass: Start date from the expression base/predecessor date, Due date from the computed RHS, Sprint by Start date, parent/assignee/priority from the Delivery Map baseline rules.
   - Work-item Jira issues should be **Tasks**, not Subtasks, unless Preston explicitly asks otherwise. If existing work-item links point to Subtasks and Jira cannot convert them to Tasks in place, create replacement Tasks under the Epic, relate/link them to the workstream Story, update only the affected Ticket cells to the new Task smart links, and leave the old Subtasks untouched unless instructed.
   - Keep the live dependency expression as the left-hand side and recompute only the rendered `= YYYY-MM-DD` value.
   - Interpret `+ nD` as business days (Mon-Fri) unless Preston provides a holiday calendar.
   - Recompute chained expressions recursively before touching workstream release labels.
   - Set each workstream heading to the single release label implied by its latest recomputed work-item due date.
   - For TSR, pass both H1 and H2 KPI pages as release-window sources so historical WS tags do not become `Before SafeART 0.21`.
   - If Preston says stories/workstreams moved to Product Refinement should be skipped, freeze any workstream whose heading contains `product refinement`: do not recompute its due-date cells, do not replace its heading label with a SafeART release, and preserve that heading exactly.
   - If a formula cannot be fully resolved because a predecessor due date is blank, but the cell already contains a rendered RHS date (`expr = YYYY-MM-DD`), keep that cell unchanged and use the existing RHS date only as a fallback for release-label derivation; record the fallback in the task artifacts/final report rather than failing or inventing a date.

## Quality bar / acceptance checklist

A Delivery Map is ready when:

- the page clearly distinguishes itself from the source spec,
- the top-level skeleton is `Page Purpose` → `Related Links` → `Workstreams`,
- workstreams are in release order,
- workstreams are split at useful capability boundaries,
- every workstream has a one-sentence goal statement,
- every workstream has one complete table with the standard columns,
- work items are assignable at PD / FE / BE granularity,
- ticket gaps remain visible rather than hidden,
- spec references either deep-link the exact source section or, when Preston wants the table itself to carry the useful detail, inline explicit acceptance criteria per work item,
- wording is normalized across the page,
- the artifact is readable by managers and actionable for domain owners.

## Common pitfalls

1. Treating the Delivery Map like a spec and over-explaining runtime behavior.
2. Keeping workstreams too large to assign cleanly.
3. Organizing by subsystem ownership instead of release sequence.
4. Hiding missing tickets or unknown due dates.
5. Mixing multiple subtitle patterns across the page.
6. Using generic work-item names that still need decomposition.
7. Leaving spec links at the top-page level instead of the exact story.
8. Adding summary/history helper sections the user did not ask for.
9. Decomposing to engineer subtasks instead of stopping at assignable planning granularity.

## Output contract

When using this skill, the final artifact should make these explicit:
- Why the page exists
- In scope / out of scope per workstream where needed
- Impacted domains (through PD / FE / BE work items and owners)
- Dependency assumptions
- Traceability to spec and tickets
- Open gaps where tickets/owners/dates are still missing

## Supporting files

Use:
- `templates/delivery-map-template.md` for a starter skeleton
- `references/format-rules.md` for the condensed rule set extracted from the TSR exemplar
- `references/tsr-due-date-maintenance.md` for due-date / release-tag refresh rules
- `references/due-refresh-product-refinement.md` for the skip/fallback pattern when product-refinement workstreams must be frozen during due-date refreshes
- `references/delivery-map-gantt.md` for WS-section / work-item-task Mermaid Gantt generation with KPI release checkpoints
- `scripts/delivery_map_due_refresh.py` for repeatable Confluence ADF due-date recalculation and workstream release-tag updates
- `scripts/delivery_map_gantt.py` for generating `.mmd` plus Discord-safe `.txt` Mermaid Gantt files from a Delivery Map
