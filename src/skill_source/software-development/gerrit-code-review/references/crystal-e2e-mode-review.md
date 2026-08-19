# Crystal E2E-only mode review notes

Use when reviewing Crystal / Angular Playwright patches that add deterministic E2E-only seed data, synthetic modes, DB seed helpers, or recorded production-shaped fixtures such as Seshat vehicle-status captures.

## Recorded-data placement tests

When a patch replaces synthetic vehicle-placement cases with recorded runtime data, separate **input realism** from **assertion quality**. A realistic payload does not prove the UI placement is tested correctly.

1. Trace each expected value to its source. If the assertion reads `data-block-id` / `data-sub-block-id` attributes that the template binds directly from the same vehicle model used as the expected value, that check only validates propagation—not placement.
2. A visibility check plus finite `top` / `left` coordinates is insufficient. Any incorrect but finite result from the positioning pipes can pass.
3. Retain or add a geometric assertion that the rendered vehicle anchor lies on the expected Konva block/sub-block segment, using the recorded status as the input. Compare against the prior patch set when the replacement deletes geometry helpers; removed assertions often reveal a regression hidden by the final diff.
4. For split rendered segments (for example one recorded sub-block expanded into several display segments), normalize IDs only as a supplement to the geometric check, not as its replacement.
5. Verify recorded fixture integrity independently: JSON parses, records are chronological when sequence matters, configured/test vehicle IDs agree, required placement fields exist, and overlap records route to the correct map.
6. If the integrated Crystal/Unicorn/Thalos environment is unavailable, run build, lint, unit tests, and Playwright `--list`; explicitly state that discovery is not execution and do not treat CI `Verified+1` as proof that this E2E scenario ran.

## Lesson from Gerrit change 7965

A patch added an E2E-only CAN schedule (`modeE2E`) by inserting directly into `can_schedules` during Playwright setup. Static/build/unit checks passed, but review found a UI consistency issue:

- The seed marked the schedule as system-defined (`is_user_defined = false`).
- The normal translation maps only had `modeA`, `modeB`, `modeC`, `modeD`, and `modeO` under `can` / `canWithCode`.
- The patch added a one-off calendar fallback (`?? 'E2E'`) in `plan-schedule.component.ts`.
- Other views still rendered direct transloco keys such as `can.modeE2E` / `canWithCode.modeE2E`.
- Tests asserted the raw key text, which normalized broken user-facing labels.

## Review checklist for similar patches

1. If a test-only fixture creates a record consumed by production UI code, verify every production rendering path for that record type, not just the path touched by the test.
2. Match classification fields to the requirement, not merely the visible string. If Jira describes a custom/user-defined schedule, the seed must set `is_user_defined = true`; a test named “user defined” is not evidence when its fixture says `false`.
3. Trace whether the changed production path even receives the classification field. A calendar mapper that only receives `canSchedule.name` can pass for both system and user-defined records, so an E2E assertion on the calendar title may still pass with a semantically invalid fixture. Validate the source/list, confirmation, preview, and audit paths too.
4. For non-user-defined seeded schedule/mode names, check all i18n maps used by the UI (`can`, `canWithCode`, detail/preview/audit labels, dialogs, radio buttons).
5. Watch for tests that assert fallback keys (`can.foo`, `canWithCode.foo`) instead of intended user-facing text; this often means a missing translation has been baked into the expected result. Renaming an expected raw key (for example `can.modeE2E` to `can.E2E`) does not fix the invalid rendering contract.
6. Prefer either:
   - add full translations for the synthetic system mode and test the intended label; or
   - mark the fixture as user-defined if it should intentionally display its literal name and bypass system translation.
7. For E2E setup projects that reset and then seed a DB, confirm the seed runs between reset and auth/storage-state creation, and that the Playwright config makes browser projects depend on the setup project.

## Follow-up patch sets that claim to fix a placement-oracle finding

1. Re-query Gerrit detail, comments, and current revision; do not assume the author's update is PS2. Record the exact current patch-set number and SHA, and confirm it again before reporting.
2. Compare adjacent **meaningful** revisions. A direct PS1→latest diff after a rebase can be polluted by unrelated target-branch changes; inspect the post-rebase patch-set deltas or use stable patch IDs to isolate the actual response.
3. Confirm the fix restores an independent oracle:
   - resolve the expected rendered sub-block from recorded block/sub-block and split/cross-view rules;
   - locate that segment in the selected M1/M2/M3 geometry;
   - independently derive the expected milepost percentage;
   - reconstruct the expected point;
   - require the rendered vehicle anchor to be on the segment and within a small tolerance on both axes.
   DOM `data-*` attributes may remain as diagnostics, but must not be the placement oracle.
4. Validate fixture joins as data contracts: status IDs and expected-value IDs must be one-to-one, unique, ordered when sequence matters, and within valid ranges. Resolve every record to an existing map shape, including polygon/Line-rendered segments and split sub-blocks.
5. Recompute expected percentages from the authoritative producer topology when available. For Unicorn-style topology, mirror `_find_sub_block_milepost_range`: select all blocks matching `block_id` and, when present, `sub_block_id`; take the minimum/maximum endpoint mileposts; then verify `(milepost - min) / (max - min)` against every fixture value. This catches a self-consistent but wrong expected-value fixture.
6. Sweep for temporary focused tests such as `test.describe.only` before approving the follow-up. Confirm the corrected scenario is part of normal Playwright discovery.
7. Report the old finding explicitly as fixed/partial/still-present/obsolete. Keep full integrated E2E execution distinct from `--list`, build, lint, unit tests, and Gerrit `Verified+1`.

## Verification commands that helped

```bash
# Exact patch set review basics
git diff --check HEAD^ HEAD
npx tsc --noEmit --pretty false -p apps/crystal/tsconfig.spec.json
npx nx lint crystal --skip-nx-cache
npx nx test crystal --skip-nx-cache --runInBand
npx nx build crystal --skip-nx-cache

# Inventory mode translation/rendering surface
git grep -n "modeE2E\|can.mode\|canWithCode\|systemCanSchedule" -- apps/crystal/src apps/crystal/e2e

# Follow-up hygiene: no accidental focused suite
git grep -n '\\.only(' -- apps/crystal/e2e
```

If full Playwright execution is blocked by local setup, still run `playwright test --list` to verify project/test discovery and report the setup limitation separately from semantic findings.
