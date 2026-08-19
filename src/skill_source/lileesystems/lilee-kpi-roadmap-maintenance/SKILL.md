---
name: lilee-kpi-roadmap-maintenance
description: Refresh Lilee KPI and roadmap Confluence pages from one or more Delivery Maps and Jira schedule evidence while preserving the existing ADF packaging, shared milestone columns, and untouched page regions.
version: 1.0.0
---

# Lilee KPI / Roadmap Maintenance

## Use this skill when

- a KPI or roadmap page must be synchronized from multiple feature Delivery Maps;
- release labels, compact work-item dates, tickets, owners, or milestone summaries are stale;
- Jira Start date, Due date, status, or assignee must be represented alongside Delivery Map scope;
- a prior-period KPI page defines the required visual packaging.

Use `lilee-confluence-adf-authoring` alongside this skill for the general Lilee ADF house rules. This skill specializes the source-merging and KPI packaging workflow.

## Source hierarchy

1. Read the live target KPI page in ADF.
2. Read the prior-period KPI page as the packaging precedent.
3. Read every cited Delivery Map in live ADF as the source for workstreams, work items, tickets, owners, dependencies, and due dates.
4. Read cited Jira issues with named field metadata when Start date, Due date, status, or assignee matters.
5. Trust live fields over expectations. If a user expects a Jira date but the live field is null, preserve the gap explicitly and report it; never derive Due date from Start date alone.

## Required workflow

1. Resolve every Confluence tiny link to a numeric page ID and verify the returned title.
2. Fetch the target, prior-period precedent, all Delivery Maps, and Jira evidence before drafting.
3. Identify the exact target `layoutSection` / `layoutColumn` regions for each feature or category.
4. Parse each Delivery Map structurally:
   - workstream heading and native status;
   - goal/subtitle;
   - Story Ticket;
   - work-item ID, function, ticket, assignee, and due expression/date.
5. Normalize schedules without inventing data:
   - explicit release statuses win;
   - concrete due dates may derive a KPI release label only when the source has no explicit label and the target release windows are authoritative;
   - explicit `Target TBD` and `Product Refinement` remain non-release statuses;
   - unresolved dependency expressions remain visible.
6. Repackage into the existing KPI style, preserving category order and layout columns.
7. Build a full-page ADF candidate, but mutate only the governed regions.
8. Validate, apply a live-body drift guard, write, read back, and verify.

### Summary-only refresh after a user edit

When the user says that they edited the KPI page and asks to reorganize the summary:

1. Re-read the newest live target ADF after the user's edit. The live left columns are the immediate source of truth for this pass.
2. Do not reuse an earlier target snapshot or rebuild the summary from stale Delivery Map artifacts.
3. Derive each right-column summary only from workstreams that still exist in the corresponding live left column.
4. Remove stale release waves and milestone text when the user removed or re-scoped a workstream.
5. Replace only the uniquely identified summary-column nodes. Preserve every left-column detail and all other page nodes exactly.
6. Fill an empty summary in the same requested scope only when the live left column has clear content to summarize. Do not invent absent scope.
7. If the user requests Simplified English, use pragmatic Simplified English:
   - active descriptive sentences;
   - one release fact per sentence;
   - no more than 25 words per sentence;
   - consistent technical nouns;
   - no decorative wording, hedges, or synonym rotation.
8. Keep every release label as a native ADF `status` node, even when the prose is simplified.
9. Before write-back, mask only the edited summary columns and prove that the complete remaining ADF is unchanged.
10. After read-back, verify that removed workstreams no longer appear in summary text and every new summary group persisted.

## KPI packaging rules

- Preserve the target page's current `layoutSection` / `layoutColumn` scaffold.
- Do not paste Delivery Map tables into the KPI page. Repackage workstreams into manager-readable nested lists.
- For each feature, include:
  - heading with native status controls and owner mention(s) only when grounded;
  - scenario-style blockquote;
  - Epic / Delivery Map inline smart links;
  - ordered workstream list;
  - compact nested work-item lines.
- Compact work-item lines use native Jira `inlineCard`, assignee `mention`, and concrete `date` nodes.
- If no ticket exists, use the source work-item description; do not invent a link.
- If no assignee exists, show `Assignee TBD`.
- Represent due evidence distinctly:
  - explicit `skip` → `Due skipped`;
  - unresolved expression → `Due: <source expression>`;
  - blank source → `Due TBD`;
  - resolved date → native Confluence `date` node.
- In a shared `Summarized milestones` column, give each feature its own label and status list. Never merge a new feature's milestones into the previous feature's list.

## Release handling

- Release identifiers use purple status controls.
- `Target TBD` and `Product Refinement` use non-release status controls and do not count as committed release waves.
- When source workstream releases collapse, rebuild the feature heading and summary from the current unique release set; remove stale waves.
- Do not replace an explicit `Target TBD` merely because one work-item dependency chain can be calculated.
- If release labels are derived from due dates, record that derivation in task evidence.

## Verification contract

- Candidate ADF validates and remains TOC-first.
- Only the exact governed top-level regions changed.
- A live refetch immediately before PUT matches the candidate base; otherwise abort.
- Read-back contains representative headings, Jira links, status nodes, mentions, and dates for every refreshed feature.
- Untouched top-level nodes remain unchanged.
- For authored semantic comparison, normalize only Confluence renderer behavior:
  - added `localId`;
  - added `__confluenceMetadata`;
  - merged adjacent equivalent text nodes;
  - omitted empty `content: []` on empty paragraphs.
- Never normalize substantive node types, URLs, status values/colors, mention IDs, or date values.
- Page width is reported as unverified unless a width-capable API was used.

## Supporting reference

See `references/multi-source-refresh.md` for the condensed extraction, release-derivation, REST write-back, and round-trip comparison recipe.
