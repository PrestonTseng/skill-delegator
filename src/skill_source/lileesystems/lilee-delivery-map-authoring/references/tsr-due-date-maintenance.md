# TSR delivery-map due-date maintenance

Use this when Preston asks to refresh the TSR Delivery Map's computed due dates or workstream release labels after estimate changes.

## Source of truth

1. Read the **live Confluence page in ADF first**.
2. Treat the **current left-side due expression in each row** as the scheduling source of truth for the refresh pass.
3. Recompute the rendered `= YYYY-MM-DD` value from that live expression; do not reuse an older local draft.

## Calculation rules

- `+ nD` means **business days (Mon-Fri)**, not calendar days.
- Unless Preston provides a holiday calendar, do **not** skip holidays beyond the normal Mon-Fri rule.
- Recompute chained expressions recursively, including:
  - `WSx.y + nD`
  - `max(WSa.b, WSc.d) + nD`
  - `YYYY-MM-DD + nD`
- Preserve the original expression text and rewrite the cell as:
  - `original expression = YYYY-MM-DD`
- When a workstream/story has been moved to **product refinement**, skip it for due-date and release-label recalculation. Preserve its heading/status and due-date cells exactly, and do not let it pull neighboring workstreams into a release window.
- If a formula references a dependency row whose due date is blank, do not invent the missing date. Leave that row unchanged unless another explicit rendered RHS date in the same cell can be safely preserved as evidence, and record the fallback in the run summary.
- If the user says to skip stories/workstreams moved to **Product Refinement**, treat headings/status labels containing `product refinement` as frozen:
  - do not recompute their due-date cells;
  - do not derive or rewrite their release labels;
  - still allow downstream non-skipped workstreams to use any existing rendered RHS date from those rows if a formula depends on them.
- If a formula references a dependency whose due-date cell is blank or otherwise unresolved, do **not** invent a date. Prefer keeping the current rendered RHS date in the formula cell as a fallback for release-label derivation, record the fallback in the run summary, and leave the cell text unchanged unless a valid recomputation is possible.

## Release-status refresh rules

- Derive each workstream heading's release status from the **latest due date among its work items**.
- When a heading currently carries multiple release labels but the recomputed latest due date lands in one release window, **collapse it to a single status label**.
- If the latest due date lands after the last known release window, use an `After SafeARt X` style label only when no later release window is available.

## Release-window grounding

When the KPI release table is incomplete:

1. Use the live KPI page(s) as the primary source for explicit release windows.
2. If later windows are missing but the KPI already implies a continuing fixed cadence, extend from the latest explicit window and call that out as an **inference**, not a hard source quote.
3. Record the basis used for any inferred windows in the task plan artifacts.

## Automation script

Use the bundled script for repeatable refreshes:

```bash
python scripts/delivery_map_due_refresh.py \
  --page-id <delivery-map-page-id> \
  --release-page-id <kpi-page-id-1> \
  --release-page-id <kpi-page-id-2> \
  --out-dir /opt/data/plans/<date>-<task>/due-refresh \
  --write
```

For the current TSR map, use both KPI release-window pages:

```bash
python scripts/delivery_map_due_refresh.py \
  --page-id 3796664324 \
  --release-page-id 3614048258 \
  --release-page-id 3645505599 \
  --out-dir /opt/data/plans/<date>-tsr-delivery-map-due-refresh/write-run \
  --write
```

Script behavior:
- fetches the live Confluence page in `atlas_doc_format` using `ATLASSIAN_API_KEY`;
- extracts all work-item rows structurally from ADF tables with `Work Item` and `Due Date` columns;
- recomputes `WSx.y + nD`, `max(WSa.b, WSc.d) + nD`, and `YYYY-MM-DD + nD` recursively;
- rewrites only formula due-date cells as `original expression = YYYY-MM-DD`;
- derives each workstream heading release status from that workstream's latest resolved due date;
- fetches release windows from one or more KPI pages (`SafeART X: start - end` text);
- emits `before-body.json`, `after-body.json`, `summary.json`, and after `--write`, `readback-body.json` / `readback-summary.json` for verification.

## Verification checklist

- Re-read the page after writeback.
- Confirm representative recalculated due-date cells persisted.
- Immediately run the refresh logic again against read-back ADF; a clean run should report `0` remaining due-date changes and `0` remaining release-label changes. If a second pass finds more changes, write that pass too and repeat until stable or blocked by an explicit unresolved dependency.
- Confirm every changed workstream heading persisted with the recomputed release label.
- Confirm TOC-first and non-targeted content remained intact.
