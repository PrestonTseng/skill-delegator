# Mock ADS track-map identifiers and independent motion controls

Use this reference when a standalone mock ADS publishes Type 2 vehicle positions that disappear on Crystal M1/M2/M3, or when test scenarios need to separate initial positioning from autonomous route progression.

## Identifier contract

Thalos track data distinguishes:

- `SubBlock.id`: directional/internal route identity, e.g. `H1T_L`, `H3T_R`, `AV1T_R`, `C5T_2_R`.
- `SubBlock.name`: externally reported/display identity, e.g. `H1T`, `H3T`, `AV1T`, `C5T_2`.
- `block_id`: physical occupancy identity, e.g. `H1T`, `C5T`, `AV-1T`.

Keep these layers separate:

1. Route planning and mission geometry use directional `SubBlock.id`.
2. Type 2 `sub_block_id` uses authoritative `SubBlock.name` so Unicorn can calculate milepost percentage and Crystal can resolve the M1–M3 Konva shape.
3. Type 13 occupancy uses physical `block_id`; do not change occupancy IDs merely to satisfy frontend rendering.

Crystal filters vehicles by service `blockId` and positions them by resolving `subBlockId` to a shape. Unicorn normalizes special physical blocks such as `AV-1T` to service `AV1T`, but passes a non-empty MQTT `sub_block_id` through unchanged. Publishing directional IDs such as `H3T_L` therefore makes the vehicle disappear when Crystal only has shape `H3T`.

Regression coverage should verify every configured route segment has both:

- a valid internal directional ID and contiguous geometry;
- the expected externally reported name from the copied authoritative Thalos constants.

For M1/M2/M3 splits such as `C3T_1`, `C5T_2`, and `W6T`, preserve the base external name; Crystal performs its own percentage-based display subdivision.

## Independent controls

Expose separate, default-on settings rather than one combined automation switch:

- `MOCK_ADS_AUTO_POSITION_ENABLED=true`
- `MOCK_ADS_AUTO_DRIVE_ENABLED=true`

Recommended behavior matrix:

- `true / true`: current full-auto behavior.
- `true / false`: position at the first service-line location, then hold at speed zero for manual movement.
- `false / true`: do not teleport; autonomous progression may begin only after an external/manual position exists on the mission path.
- `false / false`: fully manual position control while Type 2 publication continues.

Guardrails:

- Gate every automatic positioning path, both before and after departure time.
- When auto-drive is disabled, do not advance mission indexes, return to parking, or overwrite externally patched block/sub-block/milepost.
- Keep command reception and Type 4 acknowledgements active in all modes.
- Defaults must preserve existing E2E behavior.
- Document that local-build services require `docker compose up -d --build --force-recreate mock-ads-1` after source changes.

## Verification

1. Write red unit tests for external sub-block names and all four control combinations.
2. Retain Type 13 physical-block ordering regressions.
3. Run service-local tests, Ruff, compileall, Compose config, and Docker builds.
4. Run a real GraphQL/manual-mode loop with the target SafeART version.
5. Observe actual Crystal M1/M2/M3 rendering, not only MQTT or GraphQL payloads; capture each route segment's internal ID, Type 2 reported name, block, percentage, and rendered vehicle count.

### Mission-acceptance invariants when auto-positioning is disabled

A manual-mode test that patches position only **after** command acceptance cannot detect activation-time rewrites. Add explicit pre-position-before-command coverage:

- If the vehicle is already on the mission path, mission acceptance must preserve its block, reported/internal sub-block, milepost, and lane rather than snapping to the first waypoint.
- Resolve the supplied position against the authoritative path using physical block, reported or internal sub-block identity, and inclusive milepost bounds.
- Initialize both the internal mission index and published waypoint index to the matched segment. A later valid route segment must be accepted, not rejected merely because it is not segment zero.
- Reject positions with a wrong block/sub-block or a milepost outside that segment. Do not make the fix a permissive “any non-empty position is valid” branch.
- Preserve the existing auto-position-enabled handoff contract; only the disabled branch adopts manual geometry.

Use TDD with at least three cases: first-segment midpoint preserved, later route segment preserved with aligned index, and out-of-path position rejected. Observe the first two tests fail against the old activation logic before implementing the fix.

### Four-mode integration sequencing

Use a fresh database/stateful-service reset between scenarios that leave an active mission. Clear or overwrite scenario artifacts at the start so an aborted run cannot make stale JSON look like new evidence. Prefer state-based polling over fixed sleeps.

For `auto-position=false / auto-drive=true`, cover two distinct boundaries, using fresh state when needed:

1. **Yard suppression:** dispatch through GraphQL while still parked and verify command receipt does not populate block/sub-block.
2. **Activation preservation:** manually place the vehicle at a non-boundary midpoint on the first authoritative segment **before** dispatch, then dispatch a fresh mission. Immediately verify mission acceptance preserved geometry and selected path index zero; poll until Thalos authorizes movement and the milepost changes.

Do **not** rely only on dispatch-then-patch testing: it proves subsequent driving but misses mission-activation teleports. Also do **not** wait for a post-departure `WAITING_FOR_MANUAL_POSITION` state before placing the vehicle. Thalos may keep the departure signal RED while the vehicle remains in the yard; waiting for that state can deadlock the harness or outlive the mission's departure window. A fixed timeout that fails while the state still says `DEPARTURE_SIGNAL_RED` is a harness-ordering failure, not proof of an auto-drive defect.

For `auto-position=true / auto-drive=false`, verify the first position is applied and remains stable at speed zero. For `false / false`, pre-position a later valid route segment before dispatch, then verify mission acceptance preserves geometry, aligns the path/waypoint index, and continues publishing Type 2 at speed zero. Keep `true / true` as the complete GraphQL loop and final parking/occupancy gate.

### Browser-level Crystal evidence

When normal browser automation is unavailable, use an isolated temporary headless Playwright workspace rather than downgrading to payload-only evidence:

1. Install Playwright and Chromium under `/tmp`; do not add dependencies to the repo.
2. Keep testbed credentials out of source, logs, screenshots, and evidence; inject them only at runtime.
3. Log into the actual deployed Crystal UI and poll mock ADS `/debug/state` for map-specific target blocks.
4. Navigate to M1, M2, and M3 while the vehicle is in a distinctive block for each map.
5. Capture screenshot, URL, body-visible vehicle label/milepost/speed, canvas count, block/sub-block metadata, and browser console errors.
6. Visually inspect the screenshots; canvas count plus a correct MQTT payload alone does not prove the vehicle rendered.

The evidence record should pair each screenshot with the exact runtime state and should demonstrate that externally reported sub-block names have no directional `_L`/`_R` suffix while internal route geometry still does.
