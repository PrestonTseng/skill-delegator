---
name: jira-ticket-writer
description: Draft and push well-structured Jira tickets for Lilee Systems' SafeART (SART) project. Handles Epic, Task, Story, and Bug workflows; Epic tickets stay short and link to a Confluence source-of-truth page.
---

# Jira Ticket Writer for Lilee SafeART

## Overview

Drafts Jira tickets for the SafeART project (SART board) and optionally pushes them via Atlassian MCP. Handles four ticket types — **Epic**, **Task**, **Story**, and **Bug** — across three workflows: quick creation from a brief description, converting discussion conclusions into tickets, and updating existing tickets.

**Out of scope:** Epic-level Confluence design docs. If the user is starting from a feature idea that needs a Confluence design first, route to **epic-design-doc**. This skill takes over once the design is settled and the Jira Epic + Stories need to be opened.

## Step 1: Determine the workflow

| Signal | Workflow |
|---|---|
| User gives a short description and says "open a ticket" / "幫我開 ticket" | **Quick Create** |
| User has been discussing a topic (often referencing Confluence) and says "convert to ticket" / "轉成 ticket" / "based on what we discussed..." | **Discussion → Ticket** |
| User mentions an existing SART-XXXX and wants changes | **Update Existing** |

## Step 2: Classify the ticket type

- **Epic:** user references a Confluence design doc (page ID or URL) and wants the umbrella Jira ticket. Often follows immediately after using `epic-design-doc`. Phrases: "open the Epic for [design doc]", "create the SART Epic ticket".
- **Bug:** observed incorrect behavior. Phrases: "error", "bug", "wrong", "not as expected", "錯了", "壞了"
- **Task:** concrete, well-scoped work — bug fix with known scope, refactor, config, CI/CD, test automation, infra. Outcome is bounded and clear.
- **Story:** feature-level capability under an Epic. Describes *what* from a higher perspective.

If ambiguous between Task and Story → default to Task (more common). If ambiguous between Bug and Task/Story → ask one short question to disambiguate.

If the user wants an Epic but has no Confluence design doc yet, suggest: "Epic tickets in this project are stubs that link to a Confluence design doc. Want to design it in Confluence first using `epic-design-doc`, or do you have an existing doc to link?"

## Step 3: Draft the ticket

Read the appropriate template:

- **Epic:** `references/epic-template.md`
- **Task:** `references/task-template.md`
- **Story:** `references/story-template.md`
- **Bug:** `references/bug-template.md`

Follow templates exactly. They contain the section structure, formatting rules, and worked examples.

### General writing rules

1. **Language:** English for ticket content. Discussion / clarification can be in Chinese if user prefers.
2. **Tone:** Precise, technical, neutral — no speculation, no implementation details.
3. **Terminology:** Use SafeART standard terms consistently — Mission Executor, Nibble Executor, ADS Agent, FSM, MA, DOM level, ARK Code, WSS, Faramund, Felicia, Safety Server, JPS, MMS, M5 Table, Manual Mode, Operating Day, Bulletin (TSR), etc.
4. **Ticket titles must stand alone:** Write summaries so a reader can understand the work from Jira alone, without needing the companion Confluence page open. Do **not** use only workstream IDs or page-local labels such as `[WS1.2]`, `Workstream 3`, or `Phase A` as the meaningful part of the title. Use an action-oriented, domain-specific summary that names the system and the expected outcome.
5. **Confluence smart-link rule:** When a Confluence page uses an inline Jira smart link, do **not** repeat the ticket title again in adjacent prose just to make the link readable. Inline Jira links already render the key, title, and status; duplicate text adds clutter.
6. **Revision row:** Today's date (YYYY-MM-DD), author "Preston", description "Initial Version" for new tickets.
7. **R numbers (Task / Story):** ALL R numbers and sub-numbers MUST be bold: `**R1:**`, `**R1.1:**`.
8. **Testability:** Every requirement must be verifiable by another engineer.

### Workflow specifics

**Quick Create:** Extract the core problem / feature → classify → draft in English → present in code block → confirm before push.

**Discussion → Ticket:** Synthesize the discussion into structured content.
- For Epic: pull the title from the Confluence design doc, derive the Summary from its Why section, link the page in Design Doc.
- For Task / Story: organize conclusions into R-numbered requirements.
- For Bug: extract Actual vs. Expected.
- If the discussion references Confluence pages, fetch them first via `Atlassian:getConfluencePage`.

**Program / roadmap / onboarding Epic pattern:** when the work is an ongoing execution program rather than a single implementation chunk:
- Put the full plan, checkpoints, and evidence-tracking format in **Confluence**.
- Create **one Jira Epic** as the umbrella ticket.
- Keep the Epic intentionally short: Summary → Design Doc link → Revision.
- Put all future Story / Task children under that Epic instead of duplicating the roadmap into Jira.
- If the Confluence page is meant to be shared by the manager and the assignee, prefer a hybrid format: each stage should show purpose, owner, checklist, expected outputs, and review gate.

**Update Existing:** Fetch the current ticket via `Atlassian:getJiraIssue` → show user what's currently there → produce a revised description → add a new row to the Revision table with today's date and a short description of the change → push via `Atlassian:editJiraIssue`.

**Environment field format pitfall (Jira / Atlassian MCP):**
- The `environment` value must match the call's `contentFormat`.
- For create calls with `contentFormat: "markdown"`, pass `environment` as a plain Markdown string in `additional_fields`; an ADF object is rejected.
- For edit calls with `contentFormat: "adf"`, provide the field value as an ADF document.
- After any metadata edit (assignee / labels / environment / severity / reproducibility), re-fetch the issue and verify the resulting fields instead of assuming the patch behaved exactly as intended.

**Bulk metadata audit / update pattern (Delivery Map, Jira planning pages, sprint hygiene):**
- First produce a read-only audit report and get explicit approval before changing Jira metadata.
- For SART Jira direct REST fallback, use `https://api.atlassian.com/ex/jira/<cloudId>/rest/api/3/...` with Basic auth from the configured Atlassian API key. This can succeed even when site-domain REST or Agile endpoints fail with permission/scope errors.
- Relevant fields observed for SART planning metadata:
  - assignee: `assignee` with `{ "accountId": "..." }`
  - Start date: `customfield_11604`
  - system Due date: `duedate`
  - Sprint: `customfield_10006`
- Sprint update pitfall: for `customfield_10006`, Jira expects the **numeric sprint id** directly, not an array or object. Example: `{ "fields": { "customfield_10006": 2841 } }`.
- When reading current sprint, `customfield_10006` may contain historical closed sprints plus the current/future one. Treat the latest sprint by start date/id as the effective sprint for comparison.
- If Agile sprint-list endpoints are unavailable, derive sprint id/date windows from issues already assigned to those sprints via JQL and `customfield_10006`; call out any sprint whose ID/date had to be inferred because no issue currently references it.
- After bulk updates, re-fetch every edited issue and verify each intended field exactly: assignee display/account, `customfield_11604`, `duedate`, and latest sprint name/id.

**Delivery Map → ticket creation baseline metadata:**
- When creating a Jira ticket from a Delivery Map work-item row, fill the basic planning metadata during creation whenever the source row/page provides or implies it:
  - assignee from the row's Assignee cell,
  - Start date (`customfield_11604`) from the left side/base date of the Due Date cell when the cell is dependency-derived,
  - system Due date (`duedate`) from the explicit rendered date, or compute dependency expressions such as `YYYY-MM-DD+5d` in business days when no rendered RHS exists,
  - Sprint (`customfield_10006`) from the sprint window containing the ticket Start date, not the Due date,
  - Parent from the workstream/story/epic pattern used by sibling tickets; if the Delivery Map has no Story Ticket but sibling work-item tasks share a parent Epic, use that same parent,
  - Priority defaults to Medium unless the source row or user states otherwise.
- Do not leave these fields blank and do not rely on Jira's default priority for Delivery Map-derived tickets.
- After creating the ticket, re-fetch and verify Start date, Due date, Sprint, Parent, Priority, and Assignee before reporting completion.

## Step 4: Push to Jira via Atlassian MCP

### Create a new issue

`Atlassian:createJiraIssue` with:

- `cloudId`: `"lileesystems.atlassian.net"` (the site domain works directly — no need to look up a UUID)
- `projectKey`: `"SART"` (unless user specifies otherwise)
- `issueTypeName`: `"Epic"`, `"Bug"`, `"Task"`, or `"Story"` based on classification
- `summary`: the ticket title
- `description`: the ticket body in Markdown / ADF. For Bugs, the description must start with `# Actual Behavior / Reproduce Steps:` and must not duplicate the Summary, Build Version, or Environment values.

**SART Bug-specific requirement:** before creating a Bug, fetch the issue-type field metadata. In this project, Bug tickets require more than the body template:
- `Severity` (custom field `customfield_11688`)
- `Reproducibility` (custom field `customfield_11700`)
- `Environment` (system field `environment`)

Use `Atlassian:getJiraIssueTypeMetaWithFields` for project `SART` + issue type `Bug` to confirm the current required fields and allowed values before create. Then pass those values through `additional_fields`. Example defaults when the reporter has not given stronger signals yet:
- Severity: `Sev-2`
- Reproducibility: `Irreproducible` for intermittent observations without a deterministic repro
- Environment: include both build version and environment name

Usually confirm with the user before calling create. Exception: if the user explicitly asks to create/open the ticket now and immediately paste it back into a source artifact (for example a Delivery Map Ticket cell), and the source row provides enough concrete scope, create the ticket directly, then verify and report the created key. Do not stop for a draft-review round in that direct-execution flow.

### Update an existing issue

`Atlassian:editJiraIssue` with:

- `issueIdOrKey`: the SART-XXXX key
- `fields`: `{ "description": "<updated markdown>" }`

For metadata-only updates (assignee / Start date / Due date / Sprint), first perform a read-only audit and present a proposed change set. Do not mutate tickets until Preston explicitly approves the exact change set.

### Delivery Map workstream ticket creation

When Preston asks to open the Story and Task tickets for a specific Delivery Map workstream (for example, `幫我開好 WS1 的 story 與 task`), use `references/delivery-map-ws-ticket-creation.md`.

Key rules:

- Read the live Delivery Map and linked source spec/backlog first.
- Default to one workstream-level Story plus one **Task** per concrete work-item row. Work-item rows must not be created as Jira Subtasks unless Preston explicitly asks for Subtasks.
- Create or locate the parent Epic, then set `parent` on the generated Story and Tasks. For Jira Task work items, the parent is the Epic; relate/link those Tasks to the workstream Story instead of making them children of the Story.
- If an earlier run accidentally created work-item Subtasks, do not assume Jira can convert them in place. Check edit metadata first; if Subtask -> Task conversion is unavailable, create replacement Tasks under the Epic, copy the relevant content, add a short note such as `Replaces work-item Subtask SART-XXXX`, link/relate the Tasks to the Story, update the Delivery Map Ticket cells to the replacement Task keys, and leave the old Subtasks untouched unless Preston explicitly asks to close/delete them.
- Fill baseline planning metadata on every generated or affected Epic/Story/Task: Priority `Medium`, Start date, Due date, Sprint, parent where applicable, and assignee when known.
- Compute dependency-style due dates using business days; Story dates roll up from child Tasks.
- If Tasks are added under or related to an existing workstream Story, update that Story in the same pass: Start date = earliest child Task start, Due date = latest child Task due, Sprint = Story start date's sprint, Priority = `Medium`, and assignee from the workstream owner when known.
- For every ticket type — Epic, Story, and work-item Task — choose Sprint by Start date, not by Due date.
- After creation, relate Tasks to the Story and add `Blocks` links for ordered work-item dependencies.
- Write all Jira smart links back into the source Delivery Map: Epic in Related Links, Story in `Story Ticket`, Tasks in row `Ticket` cells.
- Re-fetch all created issues and verify summaries, types, parent, priority, start/due dates, sprint, assignees, statuses, and links. Read back the Delivery Map and verify the cells persisted.

### TSR Delivery Map metadata audits

When Preston asks to verify Story / Task tickets from the TSR Delivery Map, use `references/tsr-delivery-map-jira-audit.md`.

Key rules:

- Extract WS Story tickets and ticketed work-item Task rows from the live Confluence Delivery Map.
- Compute work-item due/start dates from Delivery Map dependency expressions using business days.
- Detect and report conflicts where formula recomputation disagrees with an explicit page `= YYYY-MM-DD` value; ask which should win before editing Jira.
- Story start/due roll up from ticketed child Tasks; do not infer Story assignee from child Task assignees unless the source page/user states it.
- Sprint is chosen from the Jira sprint date window containing the expected due date; if a sprint ID is inferred rather than directly read, flag it before editing.

### Read

- Ticket: `Atlassian:getJiraIssue` with `issueIdOrKey`
- Search: `Atlassian:searchJiraIssuesUsingJql` with JQL, or `Atlassian:search` for a quick natural-language query
- Confluence: `Atlassian:getConfluencePage` with `pageId` and `contentFormat: "markdown"`

## Step 5: Confirm and close

After pushing:

- Report the created / updated ticket key (e.g. "SART-1234 created").
- For batch creation, draft all tickets first → review together → push sequentially on approval.
- **Delivery Map → Jira ticket flow:** when tickets are created from a Delivery Map, immediately write the created Jira smart links back into the source Delivery Map: the workstream-level Story goes in the `Story Ticket` position, and each work-item Task goes in its row's `Ticket` cell. Use the Confluence ADF authoring workflow, preserve untouched nodes/table attrs, then read back and verify the ticket cells persisted.

## Edge cases

- **User in Chinese:** discuss in Chinese, draft in English.
- **Missing information:** don't guess. Ask targeted questions. For Bugs especially: what happened, what should have happened, environment + build version.
- **Batch creation:** list multiple tickets → draft all → review together → push sequentially on approval.
- **No push needed:** sometimes user just wants a draft to copy-paste. Present the formatted ticket; no MCP call required.
- **User has only a vague feature idea, no Confluence design doc yet:** route to **epic-design-doc** instead of pushing forward with Epic ticket creation.

## Common patterns (SafeART context)

These domains come up frequently — use as terminology grounding when drafting:

- **FSM transitions:** Mission Executor, Nibble Executor, Service Executor states and transitions
- **ADS communication:** ADS Agent timeouts, position reports, MA (Movement Authority) handling, ACK protocols
- **Faramund dispatcher:** WebSocket handshake (D0–D4 down, U0–U7 up), block-by-block authorization, breakdown SOP
- **WSS (Wayside Safety System):** anomaly detection, route authorization, block occupancy
- **TSR (Temporary Speed Restriction):** Bulletin lifecycle (Disabled / Scheduled / Effective / Expired / Disabling), MA push, conflict detection on Enable On
- **E2E testing:** Playwright automation, Jenkins CI integration, regression suites
- **Schedule management refactoring:** Operating Day vs Calendar Day, mission states (DRAFT / SCHEDULED / LOCKED / ACTIVE / ERROR / COMPLETED / CANCELLED), M5 Table, Manual Mode, Strangler Fig migration (SART-1645)
- **Architecture:** Safety Server → JPS → MMS data flow
