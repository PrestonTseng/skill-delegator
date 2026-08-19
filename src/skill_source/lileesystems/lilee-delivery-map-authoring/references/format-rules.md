# Condensed Delivery Map format rules

Derived from the live Confluence exemplar **Temporary Speed Restriction (TSR) Delivery Map** (`3796664324`, tiny link `BIBM4g`).

## Page-level rules
- Top-level skeleton is:
  1. `Page Purpose`
  2. `Related Links`
  3. `Workstreams`
- Do not add a separate `Page Rules` section by default.
- Artifact language should be English unless Preston explicitly asks otherwise.
- Use Delivery Map as the feature-level planning layer between spec and KPI pages.

## Workstream rules
- Order workstreams by release sequence.
- Use numbered headings like `## 1. ...`, not `Workstream 1` labels.
- Use one compressed subtitle sentence per workstream; prefer `The system must ...`.
- Attach release target(s) to the heading as status-style labels.
- Keep one workstream = one capability boundary.
- Preserve historical already-committed workstreams as history when the page evolves; do not silently collapse them.

## Metadata block rules
- Standard metadata blocks are:
  - `Scope boundary`
  - `Current Owner`
  - `Story Ticket`
  - optional `Design Document`
- `Current Owner` is enough unless Preston asks for more handoff metadata.
- If a workstream-level ticket does not exist, leave that gap visible.

## Table rules
- One full table per workstream.
- Standard columns:
  `Work Item | Function | Deliverable / Done When | Assignee | Ticket | Due Date | Spec Reference | Notes / Dependency`
- Work items use stable IDs like `[WS6.4]`.
- Function should normally be `PD`, `FE`, or `BE`.
- `Spec Reference` should show short labels like `story 7` with deep links.
- Ticket gaps should stay visible instead of being invented away.
- Due dates may be explicit dates or dependency formulas if the page convention already uses them.

## Confluence packaging rules
- Release labels should become Atlassian status controls.
- Jira / source links should become smart links.
- Mentions should become native Confluence mentions when publishing live.
- If editing an existing Confluence page, preserve non-targeted structure and keep the established skeleton intact.

## Quality checks
- Can a reader tell why the page exists in under 30 seconds?
- Is every workstream traceable to a specific source story or section?
- Are work items assignable without another decomposition pass?
- Are missing tickets/owners/dates still visible?
- Is wording normalized across the full page?
