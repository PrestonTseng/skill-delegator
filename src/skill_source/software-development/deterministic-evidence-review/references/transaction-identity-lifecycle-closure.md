# Transaction identity and lifecycle closure reviews

Use this reference for bounded remediation reviews of filesystem transactions that lock, stage, promote, publish metadata, clean backups, and roll back through retained directory descriptors.

## Verdict separation

Issue two independent decisions:

- **Defect closure**: whether the changed production lines close each prior finding without changed-line regressions.
- **Regression quality**: whether the committed tests genuinely exercise the promised interleavings and lifecycle boundaries.

Production closure can be approved while regression quality is rejected. Do not convert a test-coverage defect into a fabricated product defect, and do not let successful temporary probes conceal a deficient committed regression.

## Closure matrix

For every prior finding, record:

1. the authoritative invariant;
2. the changed production seam;
3. the committed regression intended to prove it;
4. an independent temporary reproduction where the committed test is incomplete;
5. the exact observed final filesystem state;
6. remaining CANNOT VERIFY items.

Keep the review bounded to the named findings and changed lines.

## Identity and confinement probes

### Cooperating locks after namespace replacement

A lock file alone is not authoritative after its parent namespace is renamed. Verify that the transaction retains and locks the target-root inode before opening the namespace lock. While the first apply remains paused after locking:

1. rename the manager namespace;
2. create a replacement namespace at the lexical path;
3. invoke a second cooperating apply with a short timeout;
4. require timeout on the retained root lock;
5. prove no metadata, staging, promotion, receipt, or cleanup write reaches the replacement namespace.

### Root and namespace replacement boundaries

Probe root and manager-namespace replacement independently at:

- after lock acquisition;
- after fresh-state scan;
- after each promotion;
- immediately before metadata publication;
- after each metadata publication.

Use a sentinel in each replacement path and assert its exact directory listing and bytes afterward. Check the detached original through its retained descriptor: before commit, promoted entries and metadata must be restored there; after commit, links and metadata must remain consistently committed. Lexical-path assertions alone do not prove descriptor confinement.

### Promoted-entry identity

Rollback authorization for a promoted symlink must compare all of:

- file type;
- `st_dev`;
- `st_ino`;
- raw `readlink()` target.

Replace a promoted symlink with a new inode using the same raw target, then inject failure. Rollback must preserve the replacement and surface rollback failure. A raw-target-only check is unsafe.

Make the replacement fixture deterministic: do **not** unlink and recreate the final pathname, because a filesystem may immediately reuse the freed inode. Create a sibling symlink while the original promoted link still exists, `lstat()` both, assert their complete `(st_dev, st_ino)` identities differ, and atomically install the sibling with same-directory `os.replace()`. Record checkpoint reachability before trusting final-state assertions. After the injected failure, assert the final entry is still a symlink with the recorded replacement identity and unchanged raw target.

Prove temporary-sibling cleanup with a directory-entry-aware check such as `not os.path.lexists(sibling)`. `Path.exists()` follows symlinks and false-passes for dangling residue, so it is not sufficient cleanup evidence even when the current fixture happens to keep the target live. Put the residue assertion after the final identity and raw-target checks, and use `finally` cleanup inside the injection callback so assertion or replace failures cannot leak the sibling.

## Lifecycle probes

Model the transaction boundary explicitly:

1. lock and preparation;
2. fresh scan;
3. staging;
4. promotion with backups retained;
5. pre-commit staging cleanup;
6. metadata publication;
7. commit flag;
8. post-commit backup cleanup.

Inject failure after staging-tree removal but before metadata publication. For REPLACE, require the old raw link and exact previous metadata bytes to be restored from the still-present backup. Then inject failure after backup removal and require the committed link/metadata to remain; post-commit cleanup failure must never enter rollback.

For an initially absent root or missing chain, inject failures after preparation, operation-lock open, staging, promotion, and pre-commit cleanup. Require exact absence afterward—not merely absence of the managed link. A post-commit failure instead retains a complete, consistent committed target.

## Multi-target test trap

Read checkpoint ordering before trusting a test name. If production verifies every target immediately after `after-promote-1`, replacing target B at that checkpoint may abort before `after-promote-2`; the later branch is unreachable and only one target was promoted.

To prove group rollback, inject the replacement/failure at `after-promote-2` so both targets have actually promoted. Assert both originals are restored and the replacement root receives no writes. Report an unreachable injected branch as a concrete regression-quality defect even when an independent temporary probe proves production closure.

## Durable regression conversion pattern

When an independent temporary probe proves production closure but committed coverage is deficient, convert the probe into repository tests without changing approved production behavior:

1. **Start from a real prior managed state for rollback claims.** Apply an initial version, capture each link with raw `readlink()` and capture `managed.json` as bytes, then build a REPLACE plan from a fresh scan. Absence-only assertions do not prove exact restoration of links or metadata.
2. **Record checkpoint reachability explicitly.** Append every checkpoint name to a local trace and assert the intended branch (for example both `after-promote-1` and `after-promote-2`) was observed. A test that only asserts final state can pass without exercising the named branch.
3. **Replace only at the intended boundary.** For multi-target rollback, rename target B and create the sentinel replacement inside the `after-promote-2` callback, then raise immediately. Verify target A at its original path, target B at the detached original path, and the replacement root by exact listing and sentinel bytes.
4. **Prove backup availability at the injection instant.** Wrap the real staging-tree removal helper, call it first, then inspect the retained backup through its open directory descriptor (on Linux, `/proc/self/fd/<backup_fd>/<relative-path>`) before raising. Capture the backup's raw link target in the hook; afterward assert exact raw-link and metadata-byte restoration plus normal backup cleanup. Raising before the real removal does not cover the lifecycle gap.
5. **Parameterize namespace boundaries against one invariant.** At lock, scan, promotion, pre-metadata, and per-target metadata checkpoints, rename the original manager namespace, create a replacement containing a sentinel, and raise. Assert the checkpoint was reached, no writes entered the replacement, and the descriptor-anchored original has the correct uncommitted recovery state.
6. Run the named new regressions, the whole transaction-focused suite, then the full language-version suite, lint/format, compile, validation, build, diff, and status. If the report path is ignored but must be committed, force-add only that exact path.

These tests are expected to pass immediately when production closure was independently approved; their purpose is durable branch and state evidence, not a new production RED. Do not manufacture a product change merely to create a failing test.

## Evidence and reporting

- Run the exact focused suite fresh.
- Put additional probes only in a temporary directory unless authorized to edit tests.
- Verify HEAD, diff range, `git diff --check`, and repository status.
- Report temporary files separately from repository modifications.
- Keep CANNOT VERIFY bounded: arbitrary instruction-level races, crash/power-loss behavior, unsupported filesystems, real privilege behavior, and configured/live mutation when not authorized.
- Lead with the exact requested verdict labels, then list only changed-line production defects or changed-line regression defects. Do not reopen unrelated tasks.
