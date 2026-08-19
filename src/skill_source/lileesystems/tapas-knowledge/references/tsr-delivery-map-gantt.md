# TSR Delivery Map Gantt extraction

Use this reference when the user asks to turn the TSR Delivery Map into a Gantt chart, dependency graph, CSV, or repeatable script.

## Source of truth

- Read the live Confluence page first, preferably in ADF / `atlas_doc_format` so native Confluence dates, mentions, smart links, and tables can be parsed structurally.
- For the current TSR Delivery Map, scope often means `workstream item 6 onward`; do not include historical H1 rows unless the user explicitly asks.
- Preserve the page's explicit due-date expressions as source evidence. Do not silently replace `WSx.y + nD = YYYY-MM-DD` with only the resolved date.

## Extraction rules

For each work-item table row, extract:

- workstream number and title
- `Work Item` id, e.g. `WS8.1`
- function: `PD`, `FE`, or `BE`
- deliverable / done-when
- assignee
- Jira ticket, if present
- raw due-date cell
- resolved due date: prefer the date after `=`, otherwise the first ISO date in the cell
- spec reference
- notes / dependency

Dependency inference:

- `Due Date` expressions like `WS8.1 + 10D = 2026-09-04` create a dependency edge from `WS8.1` to the current work item.
- `max(WS10.1, WS10.3) + 5D = ...` creates edges from each listed work item.
- `Notes / Dependency` entries containing `Dependency:` or `Depends on ...` are also dependency evidence.
- SART ticket references in dependency notes can be mapped back to work item IDs when the referenced ticket exists in the extracted set.
- Literal due dates without dependency expressions are schedule anchors, not inferred dependencies.

## Gantt rendering conventions

- First confirm the intended task unit. In TSR planning, Preston may ask for either:
  - **work-item/story-level** bars (`WSx.y` rows from the Delivery Map table), or
  - **WS/workstream-level** bars that aggregate all `WSx.y` items under each workstream.
- If Preston says the task should be **WS-based** or wants to know how `PD/FE/BE` are distributed while handling each WS, aggregate by `(workstream number, function lane)`:
  - one bar per `WS × PD/BE/FE` lane;
  - if a WS has both PD and BE/FE work, show the same WS separately in each lane;
  - bar start = earliest inferred start among work items in that WS/function lane;
  - bar end = latest resolved due date among work items in that WS/function lane;
  - label compactly as `WS<N> (<item-count> items) start → end` and put detailed `WSx.y`, tickets, titles, and due expressions in JSON/CSV sidecars.
- For story/work-item-level charts, split the chart into three sections in this order: `PD`, `FE`, `BE`, and draw each table row as its own bar.
- The Delivery Map usually stores due dates, not start dates. Represent each row as a short completion window ending on the due date; default to 5 business days unless the due-date expression supplies a duration or the user gives another duration.
- Mermaid Gantt labels clip easily on dense schedules. Keep labels compact (`WSx.y short title (ticket)` for story-level, `WS<N> (<count> items)` for WS-level) and put full detail in CSV/JSON/Markdown sidecars.
- When using Excalidraw instead of Mermaid, still emit sidecar artifacts for reviewability and regeneration:
  - work-item extraction JSON/CSV,
  - WS/function aggregation JSON when using WS-level bars,
  - element JSON,
  - editable `.excalidraw` file.
- Always emit sidecar artifacts for reviewability:
  - `work-items.json`
  - `work-items.csv`
  - `tsr-gantt.mmd` or `.excalidraw` / `elements.json`
  - `tsr-dependency-graph.mmd` when dependencies are part of the ask
  - `dependencies.md` when dependency evidence is extracted

## Verification

- Validate/render Mermaid before reporting success, using local `mmdc` if available or Kroki as fallback.
- Inspect the rendered output. For dense TSR schedules, PNG can be cramped; provide SVG or Mermaid source for zoomable review.
- When using Kroki for Mermaid Gantt, prefer SVG as the review artifact and add/verify a white background if the chat/image preview shows a dark or transparent page background. A browser preview of the SVG is a reliable readability check when PNG preview contrast is misleading.
- Use `tickInterval 1month` and `todayMarker off` for multi-release TSR Gantt charts unless daily/weekly precision is explicitly requested; weekly ticks make the chart noisy.
- Report item count and missing due-date count. A useful successful run says something like: `45 work items, 0 missing due dates`.

## Repeatable-script pattern

When writing the repeatable script:

1. Support live Confluence fetch via standard Atlassian REST auth:
   - `ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN`, or
   - OAuth bearer token plus cloud ID.
2. Also support offline regeneration from saved `--input-json` or reviewed `--items-json`; this lets the user regenerate diagrams even when the current shell lacks direct REST credentials.
3. Keep Confluence-fetch, extraction, and artifact generation in one script so frequent page edits can be reflected by rerunning a single command.
4. Do not encode one session's extracted rows inside the class-level skill; keep session-specific extracted rows in the task plan directory, not persistent skill content.
