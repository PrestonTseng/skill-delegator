# Authority declaration migration review

Use this bounded, read-only pattern when an authority branch converts one aggregate declaration into per-target files while also merging already accepted mainline work.

## Pin the graph before interpreting the diff

Record exact full SHAs for the authority remote baseline, final HEAD, accepted main merge commits, migration commit, and prepared merge commits. Verify the clean worktree, expected ancestry, exact ordered merge parents, accepted `origin/main`, and final `HEAD^{tree}`.

For a prepared merge, compare protected paths against its **first parent**. A normal `git diff-tree -m <merge>` also compares against the mainline second parent and can emit a huge, misleading list of authority-only files as additions.

## Reconstruct declarations semantically

Read the legacy aggregate from the pinned remote baseline. Parse it and build a target map keyed by canonical target ID. For every final singular file, assert exact equality of schema version, target ID, root, ordered grants (list equality, not set equality), and the complete target object.

Report grant counts as an audit aid, but never substitute counts for ordered equality. Separately prove representation exclusivity: the legacy aggregate is absent and the singular directory contains exactly the expected filenames with no extras.

## Separate migration bytes from accepted-main bytes

Use three complementary comparisons:

1. Migration parent to migration commit: only declaration paths may change.
2. Authority baseline to final HEAD over protected authority payloads: delegated snapshots and lock bytes remain unchanged unless explicitly allowed.
3. Each prepared merge's first parent to the merge over protected paths: conflict resolution did not rewrite authority payloads.

When accepted main governs CI or tooling, compare final blobs directly to `origin/main`. Then parse the workflow semantically to prove exact OS list, `fail-fast`, matrix runner binding, current-ref checkout, ordered gates, and absence of branch/ref or working-directory overrides.

## History and side-effect evidence

A missing documentation file is not automatically a migration regression. Follow its path history and establish whether a pre-existing authority commit deleted it, whether it was absent from the remote baseline, and whether current tests require it.

Git history cannot prove no external command ever ran. Phrase the result as **no evidence found**. Check that the migration contains no forbidden invocation, real-root strings occur only in declaration fields, no runtime/deployment artifacts were added, and migration paths contain no executable state. Do not inspect a forbidden real delegated root.

## Fresh read-only verification

Prefer non-mutating gates:

- pytest with cache disabled and `PYTHONDONTWRITEBYTECODE=1`;
- Ruff with each subcommand's supported `--no-cache` placement;
- in-memory `compile()` when `compileall` would create bytecode;
- `git diff --check` and final porcelain status.

Do not rebuild artifacts in a strictly read-only worktree merely to duplicate credible current-ref build evidence; distinguish supplied evidence from freshly rerun checks. If a chained gate stops, later gates are not run—resume from the failed gate.

## Decision format

Return separate `SPEC COMPLIANCE` and `TASK QUALITY` verdicts, classify Critical/Important/Minor findings (including explicit `None`), and state whether the branch is safe to push. Mention whether the ignored report directory existed and list files created or modified.