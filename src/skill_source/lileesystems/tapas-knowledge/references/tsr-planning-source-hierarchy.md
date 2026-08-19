# TSR planning source hierarchy

Use this reference when splitting TSR workstreams, shaping a Delivery Map, or reconciling spec vs execution artifacts.

## Source priority

1. **Primary source for future planning:** `Backlog - Temporary Speed Restriction (TSR)`
   - Use the spec stories, scenarios, key decisions, and scope boundaries as the main basis for workstream splitting.
   - Prefer behavior boundaries and operator workflows over technical buckets.

2. **Historical source for already-planned / already-executed H1 scope:** `2026 H1 KPI`
   - Treat H1 workstreams and work items as historical fact.
   - Fill in ticket / owner / due / status data, but do not reshape the H1 structure just to make it cleaner.

3. **Secondary execution artifacts:** live Jira stories / tasks
   - Use Jira to confirm what was actually ticketed, who owns it, what release it targeted, and whether the H1 plan drifted.
   - Jira can refine mapping, but should not outrank the TSR spec when defining post-H1 capability boundaries.

## Do not use as the main planning basis

Unless the user explicitly asks for them, do **not** use these discussion pages as the authoritative source for re-splitting TSR workstreams:

- `TSR Discussion 2026-06-02_H2 Overview`
- `TSR Discussion 2026-06-02_H2 Details`

Reason: they can bias the split toward one round of discussion framing rather than the spec's durable capability boundaries.

## Splitting rules derived from this session

- Split by **feature / behavior boundary**, not by generic FE/BE buckets.
- For remaining planning, focus on **what was not yet done in H1**.
- Keep `Story Ticket` **optional** at the workstream level.
- Subtitle lines should be **specific enough to orient the reader quickly**, but still readable in about **20 seconds**.
- Under each workstream, split work items to the level that can be assigned across the three functions:
  - **PD** — workflow / UI/UX definition
  - **FE** — page implementation plan and backend API integration
  - **BE** — data flow, system design, backend implementation, and API exposure

## Delivery-map maintenance conventions

When updating an existing TSR Delivery Map rather than re-splitting scope:

- Treat due-date expressions of the form `+ nD` as **business days (Mon-Fri)**, not calendar days, unless the user explicitly provides a holiday calendar or overrides the rule.
- Preserve the original planning expression in the cell and append the resolved date in the form `original expression = YYYY-MM-DD`.
- Recompute chained expressions recursively, including `WSx.y + nD` and `max(WSa.b, WSc.d) + nD`, from the latest saved page state.
- If the handwritten `= YYYY-MM-DD` result conflicts with recursive formula recomputation, treat it as suspect planning drift. Report the conflict first; when the user confirms formula-first behavior, update both the Delivery Map resolved date and any Jira ticket metadata from the recomputed value.
- Derive each workstream heading's release status from the **latest due date among its work items**.
- If the user later adds new release windows, refresh the affected heading statuses against the same computed latest due dates instead of reworking the underlying work items.

### Jira metadata reconciliation from the TSR Delivery Map

When Preston asks to audit or correct Jira tickets from a TSR Delivery Map section:

- Story ticket dates should be aggregated from ticketed child work items: start = earliest child start, due = latest child due.
- Story assignee is not reliably encoded in the page row tables; if Preston says “story assignee is me,” set Story assignee to Preston Tseng and do not infer it from child task assignees.
- Task assignee, due date, and ticket key come from the Delivery Map row.
- Task start date should be dependency-derived: next business day after the latest dependency due date; if no dependency exists, use the completion-window convention ending on the due date.
- Sprint should be selected by matching the final expected due date to the SafeART sprint date window in Jira, then verified by reading the issue back.

## Delivery-map Gantt / dependency artifacts

When the user asks for a Gantt view or repeatable extraction script, use `references/tsr-delivery-map-gantt.md` in addition to this source hierarchy. Key conventions:

- read the live Confluence Delivery Map first;
- extract workstream rows structurally from ADF when possible;
- split Gantt sections by `PD`, `FE`, and `BE`;
- preserve raw due-date expressions while also deriving resolved ISO due dates;
- infer dependencies from `WSx.y + nD`, `max(...)`, and Notes / Dependency text;
- emit sidecar JSON/CSV/Markdown artifacts because Mermaid labels must stay compact for readability.

## Recommended page structure for TSR Delivery Map work

When rebuilding a TSR delivery page:

1. Preserve the H1 section as historical execution.
2. Add any spec-defined H1-scope gaps that were never represented in the H1 workstream set.
3. Re-split post-H1 work, especially Form B, directly from spec stories and scenarios.
4. Only after the boundary review is approved, derive draft Jira Story / Task proposals for unticketed work.