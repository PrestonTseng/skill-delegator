# TSR Delivery Map Jira audit workflow

Use this reference when auditing or updating SART Story / Task metadata from the `Temporary Speed Restriction (TSR) Delivery Map`, especially WS6 onward.

## Source order

1. Read the live Confluence Delivery Map first.
2. Extract each WS heading, its `Story Ticket`, and ticketed work-item rows.
3. Read Jira live fields for every ticket before proposing changes.
4. Report proposed Jira metadata changes and wait for Preston approval before editing.

## Fields to inspect / update

Jira fields observed for SART metadata audits:

- Assignee: `assignee`
- System due date: `duedate`
- Start date: `customfield_11604` (`Start date`)
- Sprint: `customfield_10006` (`Sprint`)

There is also a custom `Due Date` field (`customfield_11603`), but the SART tickets in this workflow used the system `duedate` as the effective Jira due-date field. Always re-read field metadata if the project configuration may have changed.

## Expected-value derivation

For work-item Task tickets:

- Expected assignee comes from the Delivery Map row's `Assignee` cell.
- Expected due date comes from the Delivery Map row's `Due Date` expression.
- Treat `+ nD` as business days (Mon-Fri), matching the TSR Delivery Map convention.
- If the page has both a formula and an explicit `= YYYY-MM-DD`, recompute the formula and detect conflicts instead of silently trusting one side.
- Expected start date:
  - if dependencies exist, use the next business day after the latest dependency due date;
  - otherwise use a completion window ending on the due date, with duration from `+ nD` when present, or 5 business days by default.

For Story tickets:

- Expected start date = earliest expected start among ticketed child Tasks.
- Expected due date = latest expected due among ticketed child Tasks.
- Do not propose Story assignee changes unless the Delivery Map or user explicitly states the Story owner; work-item assignees do not automatically imply Story assignee.

## Sprint lookup

Preferred source: Jira sprint objects attached to live issues (`customfield_10006`), because they include `name`, `id`, `startDate`, and `endDate`.

If the Agile sprint-list endpoint is not available in the current auth scope, build a sprint map by scanning SART issues and collecting distinct sprint objects from `customfield_10006`. This is a workaround for read-only audit; do not record a permanent claim that the Agile endpoint is unusable.

Sprint matching rule:

- Convert Jira sprint `startDate` / `endDate` to the local planning date convention used in the Delivery Map.
- Pick the SafeART sprint whose date window contains the ticket Start date, not the Due date. This applies to every ticket type: Epic, Story, and work-item Task.
- If a sprint such as `SafeART 0.23 SP1` is not discoverable from issue-attached sprint data, flag it as inferred from adjacent sprint windows and ask for confirmation before edits that require its sprint ID.

## Report shape before editing

For each proposed Jira change, list:

- ticket key and issue type;
- WS / work item;
- Jira summary;
- current value → expected value for each changed field;
- whether any expected sprint ID is inferred or unresolved.

Also list no-change tickets separately.

## Description / format audit for WS6+ rewrite passes

When Preston asks to inspect WS6+ Story and Task ticket content, not only metadata:

1. Treat the live TSR Backlog / spec page as the source of truth for Story content. Rewrite Story descriptions from the spec story/scenario/acceptance criteria, not from the Delivery Map's compressed execution wording.
2. Use the Story template strictly for Story tickets: `# Introduction`, `## Why`, `## Scenario`, `# Requirements`, `# Revision`.
3. Use the Task template strictly for Task tickets: `# Introduction`, `# Requirements`, `# Revision`.
4. Validate Task and Story requirement numbering structurally in the Jira ADF: every top-level and sub requirement label must be bold, e.g. `**R1:**`, `**R1.1:**`. Do not rely only on rendered Markdown text because ADF may hide mark loss.
5. Validate Revision table presence and shape strictly. The reference pattern is SART-1140's Revision table: three columns `Date`, `Description`, `Author`, with bold header text. If an existing table is missing, malformed, or disappeared during a previous rewrite, propose adding/fixing it before mutation.
6. Preserve existing revision history when practical and append a new row for the rewrite rather than replacing old rows silently.
7. Report Delivery Map rows whose Ticket cell is blank separately from Jira changes. Rows marked `[Removed]` should normally remain without new tickets unless Preston explicitly asks to recreate them.
8. Flag type mismatches explicitly. Example: if a Delivery Map `Story Ticket` cell points to a Jira Task, ask whether to treat it as a Story-style planning ticket or preserve the current issue type and adjust only content/priority.

## REST fallback note

For large read-only Jira audits where the MCP/JQL result is truncated, the direct Jira REST fallback should use the current search endpoint:

`POST https://api.atlassian.com/ex/jira/<cloudId>/rest/api/3/search/jql`

with Basic auth from the configured Atlassian API key. Avoid the removed `/rest/api/3/search` endpoint.

## Safety rule

Do not edit Jira during the audit pass. Wait for explicit user approval, and clarify whether formula-recomputed dates or explicit page `= YYYY-MM-DD` dates should win when the Delivery Map contains conflicts. For content/format rewrite passes, also wait for explicit approval of the proposed Story drafts and Task-format change list before editing descriptions or priorities.