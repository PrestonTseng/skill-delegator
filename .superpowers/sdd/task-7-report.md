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

## Concerns

None known. No external network, configured target apply, grant/pool/source edits, checked-in config update/apply, staging outside the focused amend, push, merge, Task 8 work, or `/opt/knowledge` access was used.
