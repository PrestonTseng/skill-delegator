# Mutable uncommitted-diff re-review

Use this when files, tests, staging state, or `HEAD` change while a review is in progress.

## Durable procedure

1. Record the initial `HEAD`, `git status --short`, staged names, unstaged names, and every untracked path before reading content.
2. Treat surprising test-count or behavior changes as repository mutation. Re-read status, line-numbered source, and affected tests; do not rationalize inconsistent snapshots.
3. If a regression test exists only transiently, preserve no claim about that test. Reproduce the underlying behavior with an isolated temporary fixture/probe that does not edit the repository, then anchor the finding to final-tree production lines.
4. If `HEAD` moves, inspect the commit range from initial to final HEAD, `git reflog`, final status, `git write-tree`, and `HEAD^{tree}`. Re-run tests and static checks against the final tree unless its tree ID exactly matches a previously verified snapshot.
5. For an explicit “stop before commit/push” requirement:
   - a moved `HEAD` proves the commit condition failed;
   - no configured upstream does **not** prove no push;
   - query exact remote SHA refs when credentials permit;
   - if the remote is inaccessible, report push state as unknown, with the access error separated from review findings.
6. Final output must state which snapshot findings describe, initial/final HEAD when changed, and whether files were modified by the reviewer.

## Useful read-only probes

For semantic validators, copy a known-good document fixture to a temporary directory, mutate exactly one invariant, run the normal loader, and print `ACCEPT` or stable diagnostic codes. This exposes tests that falsely pass because they never exercise the missing relation. Keep each mutation isolated so unrelated inventory/count diagnostics do not mask the intended probe.
