# Delivery Map Workstream Jira Creation Pattern

Use when Preston asks to open a Delivery Map workstream's Story and Task tickets, e.g. `幫我開好 WS1 的 story 與 task`.

## Source-of-truth discovery

1. Read the live Delivery Map page first.
2. Read the linked source spec/backlog page before making requirement claims.
3. Extract only the requested workstream:
   - workstream heading and goal sentence
   - scope boundary
   - current owner / assignee cells
   - Story Ticket cell status
   - each work-item row: ID, function, deliverable, assignee, ticket, due-date/dependency expression, spec reference, notes/dependency
4. Search Jira for likely existing duplicates before creating new issues.
5. Resolve assignee mentions to Jira account IDs only when the work-item row names a concrete person.

## Ticket shape

For one workstream, default to:

- one Story for the workstream capability
- one Task per concrete work-item row

Do not use page-local IDs like `[WS1.1]` as the meaningful title. Titles must stand alone:

- Story: `SS ARK Code Foundation and MQTT Publishing`
- Task: `Finalize Safety Server ARK Code design document`

## Assignment and planning metadata

Delivery Map → ticket creation must fill the Jira planning fields, not just title/description.

- If the Delivery Map or related links already identify an Epic/parent, set `parent` on the workstream Story and each Task to that Epic.
- If no Epic exists for the Delivery Map feature, create a short umbrella Epic first, add it to the Delivery Map Related Links, then set it as parent.
- If the workstream owner is a team or `TBD`, leave the Story assignee unassigned unless Preston says otherwise; if the source page already names a current owner, use that owner.
- If task rows name a concrete assignee, assign each Task to that person.
- Set Priority to `Medium` unless the source row or Preston states another priority. Do not rely on Jira's default priority.
- Compute Start date and Due date from the Delivery Map Due Date cell:
  - for `YYYY/MM/DD + nD`, Start date is the base date and Due date is base + `nD` business days;
  - for `WSx.y + nD`, Start date is the predecessor's computed Due date and Due date is Start + `nD` business days;
  - roll the workstream Story start/due from the child Tasks: earliest Start date and latest Due date.
- Set Sprint using SART sprint ids (`customfield_10006`): every generated ticket type — Epic, Story, and work-item Task — uses the sprint window containing that ticket's Start date, not its Due date.

## Links and Delivery Map write-back after creation

After creating the issues:

- Relate each Task to the workstream Story.
- Add `Blocks` links for ordered dependencies, where the predecessor blocks the successor. Example: `WS1.1 blocks WS1.2`, `WS1.2 blocks WS1.3`.
- Write Jira smart links back into the source Delivery Map: workstream Story goes in `Story Ticket`; each Task goes in its row's `Ticket` cell; any newly-created Epic goes in Related Links.

## Verification

After mutation, re-fetch every created issue and verify:

- key, summary, issue type
- assignee behavior matches source assumptions
- parent
- priority = Medium unless explicitly overridden
- Start date, Due date, and Sprint
- relationship links exist in the expected direction

Read the Delivery Map back in ADF and verify the Story Ticket / Ticket cells and table attrs persisted.

Record the created keys, computed dates/sprints, parent, and assumptions in the task plan directory/status file when the task is non-trivial.
