# Task 7 report: explicit upstream update workflow

## Result

DONE

Implemented explicit, non-applying source update checks and validated candidate-lock publication. Update operations are separated from target apply and repository Git operations: checks only refresh ignored cache data, proposals preserve every unselected locked identity, and the CLI atomically replaces only `config/skill-lock.yaml` after complete candidate validation.

## Delivered

- Added immutable `SourceUpdate`, `ArtifactUpdate`, and `LockUpdateProposal` evidence models.
- Added `check_updates(config, lock)` with deterministic relations for no-change, fast-forward, force-moved/diverged, moved tags, unavailable Git sources, and moved filesystem trees.
- Added `prepare_update(source_id, config, old_lock)`:
  - validates old lock/config authority first;
  - resolves the selected mutable selector, then inventories its exact resolved identity;
  - preserves every unselected `LockedSource` byte-for-model identity;
  - validates complete pool and grant authority before returning a proposal;
  - reports only canonical IDs and old/new hashes for authority-relevant artifacts;
  - reports new and removed ungranted artifacts separately.
- Added deterministic bounded human and JSON proposal/check renderers without skill bodies or source locations.
- Added `skillctl update --check`, `skillctl update SOURCE`, and `skillctl update --all` with fail-closed selector conflicts and bounded exit codes.
- Candidate publication uses the existing atomic lock writer only after every selected candidate validates. No update path calls apply, stages, commits, pushes, merges, or touches target roots/grants/pool/source configuration.

## TDD evidence

- RED: `tests/unit/test_updater.py` initially failed collection because `skill_delegator.updater` did not exist.
- RED: `tests/integration/test_update_cli.py` initially failed because `update` was not a CLI command.
- GREEN/REFACTOR focused gate: 11 update unit/integration/adversarial tests passed.
- Full regression gate: 252 tests passed (the prior 241-test contract plus 11 Task 7 tests).

## Coverage added

Local temporary filesystem and bare/local Git fixtures cover:

- no update and branch fast-forward;
- tag movement and force rewrite/divergence;
- changed and unchanged pooled/delegated artifacts;
- deleted/renamed grant blocking;
- new and removed ungranted artifacts;
- filesystem movement and offline Git;
- corrupted old lock and unknown selected source;
- selected-source-only preservation;
- `--all` validation atomicity;
- byte-stable human/JSON/check output;
- tracked config/lock inode and target nonmutation during `--check`;
- Git worktree/index/history nonmutation and lock-only update diff;
- injected candidate-write failure preserving original lock bytes and inode.

## Fresh verification closure

Correction: the earlier report did not include a fresh formatter gate and incorrectly implied the committed tree already satisfied formatting. `uv run --python 3.12 ruff format` reformatted exactly four Task 7 files: `src/skill_delegator/updater.py` and the three Task 7 test files. AST comparison of each file against the pre-format `HEAD` was identical, confirming formatting-only changes with no update-semantic change.

Fresh gates run after formatting:

- `uv lock --check` -> **Resolved 15 packages; exit 0**
- `uv sync --frozen --python 3.12` -> **Checked 14 packages; exit 0**
- `uv run --frozen --python 3.12 python --version` -> **Python 3.12.13**
- `uv run --frozen --python 3.12 ruff format --check .` -> **41 files already formatted**
- `uv run --frozen --python 3.12 ruff check .` -> **All checks passed**
- focused Task 7 tests (`test_updater.py`, `test_update_cli.py`, `test_upstream_rewrites.py`) -> **11 passed in 0.68s**
- `uv run --frozen --python 3.12 pytest -q` -> **252 passed in 8.94s**
- `uv run --frozen --python 3.12 python -m compileall -q src tests` -> **exit 0**
- `uv run --frozen --python 3.12 skillctl validate --config config` -> **Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets**
- `uv build` -> **sdist and wheel built successfully**

## Review-finding closure

A bounded follow-up closed the three Task 7 review defects without adding apply, Task 8, or network behavior:

- Cache roots are now created and traversed one lexical component at a time from the filesystem anchor with `dir_fd`, `O_DIRECTORY`, and `O_NOFOLLOW`. Every opened ancestor identity remains retained and is rechecked before/after cache writes. Update-check temporaries and source snapshots operate through retained descriptor paths, so replacing `project/var`, `cache`, `sources`, or a per-source cache cannot redirect writes.
- Lock publication now uses an anchored parent FD, fsynced unique stage, retained hard-link rollback journal, exact staged/published inode checks, directory fsync, and rollback+fsync. A post-replace reported failure restores the prior pathname bytes/inode (or prior absence); a concurrent same-bytes/new-inode replacement is never overwritten and returns `lock-rollback-unsafe`.
- Update public boundaries now translate inventory/cache/source/config/publication failures to bounded allow-listed messages. Real CLI probes assert source/outside/target/cache paths, symlink targets, injected secrets, raw exceptions, and tracebacks are absent from stderr.

### Follow-up TDD evidence

- RED (before implementation): focused regressions produced **7 failed, 31 passed**. Failures reproduced symlinked `project/var` target mutation, ancestor symlink acceptance, post-replace fsync leaving the candidate public, and raw configured-location disclosure.
- GREEN after the final ancestor-matrix expansion: focused cache/lock/update/adversarial gate produced **55 passed**.
- Full regression gate after the final expansion: **275 passed** (the prior 252-test contract plus 23 deterministic regressions).

### Fresh follow-up verification

- `uv lock --check` -> **Resolved 15 packages; exit 0**
- `uv sync --frozen --python 3.12` -> **Checked 14 packages; exit 0**
- Python gate -> **Python 3.12.13**
- `ruff format --check .` -> **42 files already formatted**
- `ruff check .` -> **All checks passed**
- Focused Task 7/cache/lock gate -> **55 passed in 2.56s**
- Real subprocess CLI symlink/non-directory ancestor matrix -> **6 passed in 1.46s**
- Full suite -> **275 passed in 10.68s**
- `compileall` -> **exit 0**
- `skillctl validate --config config` -> **Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets**
- Build to `/tmp/task7-fix-build` -> **sdist and wheel built successfully**

## Final rollback-outcome closure

The remaining rollback-operation ambiguity is closed by one explicit public-outcome state machine. After any post-publication error, the anchored public pathname is classified using both regular-file identity and exact bytes:

- exact prior inode/bytes (or prior absence) reports the original bounded publication failure;
- exact staged candidate inode/bytes is treated as a committed update and returns normally, including normal CLI proposal output;
- every other state, including concurrent same-bytes/new-inode replacement or an unprovable/different-byte state, is preserved and reports `lock-rollback-unsafe`.

Rollback replacement and rollback-directory-fsync failures are re-observed rather than guessed. Candidate-success cleanup removes the backup journal best-effort without touching the public candidate; unsafe outcomes retain any still-existing journal.

### Final closure TDD evidence

- RED: the five new focused regressions produced **4 failed, 1 passed**. Failures reproduced backup-restore failure leaving the candidate public, rollback-fsync failure leaving the candidate public, concurrent replacement during rollback fsync being misclassified, and CLI blocking despite exact candidate ownership. The already-correct prior-restored rollback-fsync case passed.
- GREEN: the same five regressions produced **5 passed in 0.20s**.
- Reviewer probe `/tmp/task7_rollback_failure_probe.py` -> `error=NO_ERROR`, `candidate_public=True`, `prior_restored=False`, `journals=[]`.

### Fresh final verification

- `uv lock --check` -> **Resolved 15 packages; exit 0**
- `uv sync --frozen --python 3.12` -> **Checked 14 packages; exit 0**
- Python gate -> **Python 3.12.13**
- Focused Task 7/cache/lock gate -> **60 passed in 2.61s**
- Full suite -> **280 passed in 11.03s**
- `ruff format --check .` -> **42 files already formatted**
- `ruff check .` -> **All checks passed**
- `compileall` -> **exit 0**
- `skillctl validate --config config` -> **Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets**
- Build to `/tmp/task7-final-build` -> **sdist and wheel built successfully**

## Atomic-replace commit-boundary closure (supersedes rollback architecture)

The second and final lock-publication correction removes public-path rollback entirely. All stage writes, descriptor chmod, file fsync, exact staged-byte/inode checks, anchored-parent verification, and prior public snapshot validation occur before `os.replace`. The successful atomic replace is now the sole commit boundary. After it returns, `write_lock_atomic` never unlinks or replaces `skill-lock.yaml`; there are no backup journals.

A post-commit directory-fsync or parent-verification error is classified by read-only observation of the public pathname. Exact staged inode plus exact candidate bytes returns committed success and preserves normal CLI proposal output. Missing, symlink, nonregular, different bytes, or any different inode (including same bytes in a concurrent inode) is preserved and raises bounded `lock-rollback-unsafe`. Any failure before replace raises bounded `lock-publication-failed`, best-effort removes only the unique private stage, and preserves exact prior bytes/inode or prior absence.

### Commit-boundary TDD evidence

- RED: two deterministic regressions at the rejected observation-to-rollback boundary both failed. For existing and initially absent locks, the old implementation respectively overwrote and unlinked a concurrent same-bytes/new-inode replacement and reported `lock-publication-failed`.
- GREEN: the regressions now inject the same concurrent states at the old rollback observation checkpoint; both public replacements remain untouched and are classified `lock-rollback-unsafe`.
- Existing rollback-expectation tests were replaced with the explicit commit contract: normal atomic success, exact candidate post-fsync success (including CLI proposal output), concurrent existing/absent state unsafe, and prepublication existing/absent preservation.

### Fresh commit-boundary verification

- `uv lock --check` -> **Resolved 15 packages; exit 0**
- `uv sync --frozen --python 3.12` -> **Checked 14 packages; exit 0**
- Python gate -> **Python 3.12.13**
- Focused lock/update/upstream gate -> **58 passed in 2.51s**
- Full suite -> **278 passed in 10.78s**
- `ruff format --check .` -> **42 files already formatted**
- `ruff check .` -> **All checks passed**
- `compileall` -> **exit 0**
- `skillctl validate --config config` -> **Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets**
- Build to `/tmp/task7-commit-boundary-build` -> **sdist and wheel built successfully**

## Concerns

The ancestor-replacement and concurrent-lock cases use deterministic checkpoint/fault injection. They verify the specified identities and commit-boundary outcomes but are not a claim of exhaustive coverage for every possible OS-level interleaving. No external network, configured target apply, grant/pool/source edits, checked-in config update/apply, push, merge, Task 8 work, or `/opt/knowledge` access was used.
