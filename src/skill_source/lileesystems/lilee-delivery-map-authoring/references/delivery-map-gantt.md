# Delivery Map Gantt generation

Use this reference when Preston asks to turn a Lilee Delivery Map into a Mermaid Gantt chart.

## Standard rendering rules

Default chart shape:

1. Use each **WS / workstream** as a Mermaid `section`.
2. Use each Delivery Map **work item row** as a Mermaid task.
3. Include a leading `Checkpoints` section when KPI release pages are provided.
4. Output both:
   - `.mmd` for normal Mermaid source handling, and
   - `.txt` copy for Discord upload, because Discord may reject `.mmd` attachments.

## Color / marker convention

Mermaid Gantt's built-in classes are used as the role colors:

- `PD` → `active`
- `BE` → `crit`
- `FE` → `done`

Do not invert this for TSR Delivery Map Gantt unless Preston explicitly asks.

## Required Mermaid settings

Use exactly this header unless Preston overrides it:

```mermaid
dateFormat  YYYY-MM-DD
axisFormat  %Y/%m/%d
todayMarker true
excludes weekends
tickInterval 2week
```

## Release checkpoints

When `2026 H1 KPI` and `2026 H2 KPI` page IDs are available, pass both as release sources:

- `3614048258` — 2026 H1 KPI
- `3645505599` — 2026 H2 KPI

The script extracts release windows like `SafeART 0.22: YYYY-MM-DD - YYYY-MM-DD` and uses the window end date as a milestone checkpoint:

```mermaid
section Checkpoints
SafeART 0.20 Release :milestone, cp_0626, 2026-06-26, 0d
SafeART 0.21 Release :milestone, cp_0808, 2026-08-08, 0d
```

For the current TSR map, Preston usually wants the checkpoint range `0.20` through `0.24`.

## Standard command

```bash
python /opt/data/profiles/tapas/skills/lileesystems/lilee-delivery-map-authoring/scripts/delivery_map_gantt.py \
  --page-id 3796664324 \
  --release-page-id 3614048258 \
  --release-page-id 3645505599 \
  --from-ws 6 \
  --checkpoint-min-version 0.20 \
  --checkpoint-max-version 0.24 \
  --title 'TSR Delivery Map - WS6 onward' \
  --out /tmp/tsr-delivery-map-ws6-gantt.mmd
```

This creates:

- `/tmp/tsr-delivery-map-ws6-gantt.mmd`
- `/tmp/tsr-delivery-map-ws6-gantt.txt`

Send the `.txt` file to Discord with `MEDIA:/tmp/tsr-delivery-map-ws6-gantt.txt` when the user asks for the file.

## Script behavior

The script:

1. Fetches live Confluence ADF using `ATLASSIAN_API_KEY`, or accepts saved ADF/page JSON paths in place of page IDs.
2. Extracts workstream headings and work-item rows from Delivery Map tables.
3. Recomputes formula due dates recursively using business days for `+ nD`.
4. Uses a formula's `+ nD` value as the task duration when present.
5. Uses a 5-business-day completion window for plain due dates.
6. Writes both `.mmd` and `.txt` outputs.
7. Emits a JSON summary with item count, checkpoint count, output paths, and missing due-date count.

## Verification checklist

- [ ] Script exits with code 0.
- [ ] Summary reports the expected `from_ws` and nonzero `items` count.
- [ ] `missing_due_dates` is 0, or any missing dates are reported before sending.
- [ ] `.txt` output exists and contains a Mermaid `gantt` block.
- [ ] Checkpoints include the requested SafeART release range.
- [ ] PD rows use `:active`, BE rows use `:crit`, and FE rows use `:done`.
