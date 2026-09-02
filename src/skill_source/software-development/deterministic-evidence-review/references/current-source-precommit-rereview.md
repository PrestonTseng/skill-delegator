# Current-source pre-commit re-review

Use this for a fresh, read-only re-review of an uncommitted vertical slice where the primary question is whether earlier blocking findings are closed.

## Snapshot discipline

- Inventory both tracked and untracked scope with `git status --short`; `git diff` alone omits new files.
- Read the binding task/spec and turn every prior blocker into an explicit closure row: `CLEARED`, `PARTIAL`, or `NOT_CLEARED`.
- Shared worktrees may change during review. Capture a narrow status/diff identity, and if any source changes, discard conclusions for affected files, reread the current source, and rerun relevant gates. State this in the report.
- Do not modify product files. Finish with `git diff --check` and a final narrow status comparison.

## Vertical-slice trace

Trace each requirement across domain/application contract, schema/migration invariant, repository SQL/transaction, API/SSR parsing and authorization, UI wiring/visibility, and tests/typecheck/build. A passing helper test does not close a finding when a later layer reintroduces it.

## High-yield adversarial probes

- **Inclusive date filters:** a date-only upper bound parsed as midnight and queried with `<=` excludes most of that day. Prefer next-day midnight with `<`, and test a row during the final day.
- **Strict dates:** JavaScript `new Date()` normalizes some nonexistent dates. Require format validation plus round-trip/canonical validation.
- **Opaque cursors/tokens:** `Buffer.from(value, "base64url")` can accept non-canonical or junk-suffixed encodings. Validate alphabet/length/padding as applicable and require canonical re-encoding before parsing payload schema.
- **Option/reference leaks:** distinguish public filter options from admin mutation options; filter disabled records and recheck admin identity at the transaction boundary.
- **Asset path disclosure:** return an authorized logical URL or presence flag, never a backing storage path.
- **Authorization races:** recheck mutable role/disabled/org state inside the write transaction, not only from session state.
- **UI authorization:** verify server-rendered navigation, page access, and mutation API independently.

Pair every hostile probe with a valid control.

## Verification ladder

Run targeted tests, database integration tests against the actual current test database, package typechecks, production build/compile, then `git diff --check` and final source-scope status comparison.

If a configured database endpoint is stale but a clearly identified disposable test database exists, derive a temporary process-local connection from that test service and rerun. Never persist credentials or rewrite configuration. Report the initial failure separately from the successful rerun.

## Decision-ready JSON-like report

Use top-level keys `verdict`, `blocking`, `nonblocking`, `previous_blockers`, `focused_checks`, `verification`, `files_modified`, and `issues_encountered`. Every blocker needs exact location, evidence, impact, and required remediation. Keep nonblocking observations separate. `APPROVE` requires `blocking: []`; any prior blocker still violating the binding contract means `BLOCK`.