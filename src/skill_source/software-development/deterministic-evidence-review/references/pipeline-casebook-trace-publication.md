# Pipeline Casebook Trace and Multi-Format Publication

Use this checklist when an immutable pipeline report must explain every gate at every analysis boundary, rather than only the terminal decision.

## Trace contract

For each `analysis boundary × entity/symbol`, preserve the authoritative gate order and copy—not recompute—each validated gate result:

- gate name and status (`PASS`, `FAIL`, `UNAVAILABLE`)
- reason codes
- value and reference levels
- event time and known-at time
- input/config identity hashes
- terminal decision, passed gates, first failed gate
- dataset, run, manifest, and decision identities

`UNAVAILABLE` must remain distinct from a valid `FAIL`: it commonly means an upstream gate prevented evaluation. Validate event/known-at causality and boundary alignment before projection.

## Human views

Provide two complementary views from the same validated result:

1. Markdown matrix: one row per boundary/entity, one column per ordered gate, followed by detailed evidence.
2. CSV: one row per gate for filtering and pivoting.

Machine JSON may retain all historical strategy cohorts, but human debugging views should select the active strategy cohort or group by strategy-specific schema. Never derive columns from the first case and render rows from mixed gate schemas; this creates malformed tables and blank/non-comparable boundaries.

Test mixed legacy/current cohorts explicitly. Require every Markdown matrix row to have the same delimiter count and every CSV row to belong to the declared active cohort.

## Coherent multi-format publication

When JSON, Markdown, and CSV claim to represent one snapshot:

1. Build and validate once.
2. Render every payload before publishing any file.
3. Require unique output names in one directory.
4. Hold one publication lock.
5. Capture old bytes for every output.
6. Write/fsync separate temporary regular files with no-follow creation.
7. Replace human views first and machine JSON last as the snapshot commit marker.
8. Fsync the directory.
9. Reopen and byte-verify every output.
10. On any failure, restore or remove every output as a group, fsync, preserve the primary exception, and clean all temporary files.

A set of atomic single-file writes is not a coherent multi-file snapshot. Add failure injection at the second/third replace and at directory fsync; assert all old bytes are restored and no temporary files remain.

## Verification ladder

- RED: missing ordered steps.
- GREEN: exact authoritative payload projection.
- RED/GREEN: mixed old/new strategy matrix.
- RED/GREEN: injected failure during later format publication.
- Targeted renderer/publication/scheduler tests.
- Full suite, formatter/linter, build/compile, shell syntax, diff check.
- Read-only replay on real immutable artifacts; verify `boundaries × entities × gates = CSV rows` and consistent Markdown columns.
- Scan exported bytes for credentials, absolute private paths, and connection details before sharing.

Keep this a reporting projection. Do not expand into strategy recomputation, storage redesign, order execution, or performance claims unless separately authorized.
