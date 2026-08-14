# Task 5 Report — Safe managed-symlink reconciliation

## Status

DONE

## Scope delivered

- Added immutable apply bindings to reviewed reconciliation plans: exact target roots, cache roots, desired managed entries, raw-link-aware current-state fingerprints, and root-existence state.
- Added `apply_plan(plan, *, lock_timeout)` with stable root/target ordered `fcntl.flock` locks at `<target>/.skill-delegator/operation.lock`.
- Re-scans every target under lock and rejects a stale lexical/current-state fingerprint before link mutation.
- Validates internal plan consistency and re-hashes each exact desired cache destination before promotion.
- Stages absolute symlinks under manager metadata, verifies exact raw staged targets, then promotes CREATE/REPLACE/REMOVE operations with per-path backups and a rollback journal.
- Publishes canonical strict `managed.json` only after every link operation succeeds.
- Restores prior links and exact managed JSON bytes on injected failure; removes only newly created empty path components; refuses to delete a destination changed to unmanaged content during rollback.
- Retains a strict bounded Task 5 `failure.json` containing the primary phase/error and bounded rollback errors.
- Added `skillctl apply`, including validated config/lock/desired/current plan reconstruction, blocked-state rejection, `--yes` confirmation for REMOVE, lock timeout, bounded deterministic errors, and idempotent output.
- Did not add Task 6 success receipts, verify/status/drift, Task 7 update behavior, adapters, network operations, or real configured-target mutation.

## TDD evidence

Initial focused RED command:

```text
uv run --python 3.12 pytest -q tests/unit/test_reconciler.py tests/integration/test_apply_cli.py tests/adversarial/test_apply_failures.py
```

Failed during collection because `skill_delegator.reconciler` did not exist. A later focused RED for forged plan consistency failed because apply accepted an inconsistent desired operation binding. Both were followed by focused GREEN runs.

## Test coverage added

- create, replace, remove, exact metadata publication, and repeatable/idempotent apply
- preservation of unmanaged files and refusal to delete hostile replacement content
- absolute created-link raw target and preservation of a valid relative managed-link raw target
- lock contention and bounded timeout
- stale plan and hostile root replacement after planning
- source-cache content tampering and staging permission errors
- injected failure after staging, after individual promotion, before metadata, and after metadata
- exact replacement rollback of raw link target and managed metadata bytes
- rollback failure surfacing and bounded failure receipt
- CLI apply success, convergence, blocked state, and explicit REMOVE confirmation

## Fresh verification

```text
uv run --python 3.12 pytest -q
183 passed in 6.59s

uv run --python 3.12 ruff check .
All checks passed!

uv run --python 3.12 ruff format --check .
31 files already formatted

uv build
Successfully built dist/skill_delegator-0.1.0.tar.gz
Successfully built dist/skill_delegator-0.1.0-py3-none-any.whl

git diff --check
(clean)
```

All tests use pytest temporary filesystems; no configured target or `/opt/knowledge` content was mutated.

## Files

Created:
- `src/skill_delegator/reconciler.py`
- `tests/unit/test_reconciler.py`
- `tests/integration/test_apply_cli.py`
- `tests/adversarial/test_apply_failures.py`
- `.superpowers/sdd/task-5-report.md`

Modified:
- `src/skill_delegator/models.py`
- `src/skill_delegator/managed_state.py`
- `src/skill_delegator/planner.py`
- `src/skill_delegator/cli.py`

## Concerns

Task 6 fresh verification and success/audit receipts remain intentionally unimplemented.

## Review-finding closure — descriptor-anchored transaction identity and lifecycle

### RED evidence

Regression tests were added before production changes for target-root and manager-namespace inode replacement, a second cooperating lock after namespace replacement, same-raw-target symlink replacement with a new inode, post-backup cleanup failure, operation-lock open failure on an absent root, absent-root staging and injected failures, root replacement at lock/scan/promotion/metadata boundaries, post-commit failure, and multi-target partial failure without replacement-path writes.

Exact RED command:

```text
uv run --python 3.12 pytest -q tests/adversarial/test_apply_failures.py
```

Result: `13 failed, 5 passed`. The failures reproduced retained absent roots, missing root/namespace checkpoints, stale lexical-path promotion and recovery, same-target replacement deletion, rollback after backup removal, and missing preparation cleanup.

### GREEN evidence

The reconciler now retains and locks target-root, namespace, and operation-lock descriptors; verifies `(st_dev, st_ino)` identities; performs transaction mutation and recovery relative to retained descriptors; journals promoted link identity; preserves all backups until the commit boundary; removes staging before metadata publication; treats completed metadata publication as committed; and restores initially absent target chains without an in-root failure artifact.

Focused gate:

```text
uv run --python 3.12 pytest -q tests/adversarial/test_apply_failures.py tests/unit/test_reconciler.py tests/integration/test_apply_cli.py
29 passed in 0.46s
```

Full fresh gates:

```text
uv run --python 3.12 pytest -q
193 passed in 6.76s

uv run --python 3.12 ruff check .
All checks passed!

uv run --python 3.12 ruff format --check .
31 files already formatted

uv build
Successfully built dist/skill_delegator-0.1.0.tar.gz
Successfully built dist/skill_delegator-0.1.0-py3-none-any.whl

git diff --check
(clean)
```

Scope remained limited to Task 5 reconciler semantics, adversarial regressions, and this report. No configured target, Task 6 success receipt/status, Task 7, network operation, push, merge, or `/opt/knowledge` change was made.

## Committed regression closure — deterministic reviewer gaps

Added durable temporary-filesystem regressions for the three reviewer-identified coverage gaps without production changes:

- a two-target REPLACE transaction that records reaching both `after-promote-1` and `after-promote-2`, replaces target B only after the second promotion, restores both targets' exact prior raw links and `managed.json` bytes, and leaves the replacement root untouched;
- parameterized `.skill-delegator` namespace replacement at `after-lock`, `after-scan`, `after-promote-1`, `before-metadata`, and `after-metadata-1`, proving all pre-commit boundaries restore the original absent state and never redirect writes into the replacement namespace;
- a REPLACE failure injected after the staging tree has actually been removed, with the test observing the exact old raw link in the still-open backup before failure and then verifying exact link and metadata restoration.

Fresh verification:

```text
uv run --python 3.12 pytest -q tests/adversarial/test_apply_failures.py -k '<three closure regressions>'
7 passed, 19 deselected in 0.22s

uv run --python 3.12 pytest -q tests/adversarial/test_apply_failures.py tests/unit/test_reconciler.py tests/integration/test_apply_cli.py
35 passed in 0.53s

uv run --python 3.12 pytest -q
199 passed in 6.78s

uv run --python 3.12 ruff check .
All checks passed!

uv run --python 3.12 ruff format --check .
31 files already formatted

uv run --python 3.12 python -m compileall -q src tests
(exit 0)

uv run --python 3.12 skillctl validate
Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets

uv build
Successfully built dist/skill_delegator-0.1.0.tar.gz
Successfully built dist/skill_delegator-0.1.0-py3-none-any.whl
```

Production closure remains approved; no production files were modified.
