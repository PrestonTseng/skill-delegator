# Exact-Pinned Lock Rebuild and Live Cutover Review

Use this checklist for a read-only pre-commit review where a generated lock is being repaired to match immutable source commits after a live target cutover. The goal is to prove that the patch repairs authority metadata without advancing source revisions or changing the managed target.

## 1. Freeze authority and diff scope

Record both local and remote authority identities before reading evidence:

- `git rev-parse HEAD` and `HEAD^{tree}`;
- branch/upstream state and exact `git ls-remote` branch SHA;
- staged, unstaged, and untracked paths separately;
- `git diff --stat`, `--name-status`, full hunks, and `git diff --check`.

For a lock-only repair, require exactly the authorized lock file and expected scalar replacements. Recheck HEAD, remote SHA, status, and diff at the end. Do not run lock, update, apply, or verify when the review scope is read-only; `verify` may publish a receipt. Prefer `validate`, `resolve`, `plan`, and `status` for non-mutating evidence.

## 2. Prove semantic lock preservation

Parse the base lock, generated lock, and candidate lock. Recursively remove only the field being repaired (normally source-level `tree_hash`) and require structural equality. Report source/skill counts, changed source IDs, resolved-commit changes, preservation of source type/canonical ID/runtime name/path/per-skill SHA, and whether generated and candidate locks are byte-identical. Do not accept a small textual diff as proof that nested evidence stayed unchanged.

## 3. Establish generated-lock provenance

If the candidate was produced in a disposable archive:

1. Compare every tracked path other than the intentionally rewritten configuration files with pinned authority HEAD by path, type, mode, symlink target, and bytes.
2. Enumerate untracked files outside generated output roots. A local `.venv` is tooling residue, not source provenance, but must not be mistaken for archive content.
3. Parse temporary source configuration and require every Git track to equal its existing lock commit.
4. Require the temporary lock and reviewed candidate to match exactly.

## 4. Reconstruct pristine source truth independently

For each repaired Git source:

1. Clone with `--no-checkout` into a temporary directory.
2. Resolve `<locked-commit>^{commit}` and require the exact SHA.
3. Check out detached, remove `.git`, and treat the tree as pristine engine input.
4. Build manifests for pristine checkout, generated cache, and live cache containing every relative path, object type, permission mode, symlink target, and regular-file byte hash.
5. Require no extra, missing, or changed paths.
6. Run the production engine's `hash_tree` against all three trees.
7. Require all hashes to equal the new lock hash, and show that the old lock hash differs from pristine truth.

Use temporary directories with automatic cleanup. Per-skill SHA equality is insufficient because source verification covers the complete source tree, including ungranted content.

## 5. Verify live convergence without mutating it

Run fresh `validate`, `resolve`, target-scoped JSON `plan`, and target-scoped JSON `status`. A converged post-cutover plan should contain only `KEEP` and `PRESERVE_UNMANAGED`, with no blockers or `CREATE`/`REMOVE`/`REPLACE`. Status should verify every desired link with zero drift, zero invalid entries, and no reasons.

Treat `PRESERVE_UNMANAGED` totals as live observations, not immutable acceptance constants. If a count differs from earlier evidence, inspect changed unmanaged paths and timestamps. Concurrent additions are non-blocking when preserved and managed convergence remains exact; report the new count honestly and require another fresh plan immediately before apply.

## 6. Prove receipt and transaction hygiene

Do not equate a non-empty receipt directory with failed-verify residue. Inspect each receipt's result, lock/config hash, desired/verified counts, and modification time relative to cutover metadata. A prior successful receipt with an older lock hash is historical evidence, not a failed receipt. A failed verification is clean when it publishes no new receipt bound to the failed configuration and leaves no source `.snapshot-*`/`.update-check-*` entries or target `staging`/`backup` residue.

## 7. Exclude wrong-target mutation

When target declarations share a physical root, compare manager metadata artifact IDs with each target's exact grant set. Exact equality with the intended target and inequality with another target is stronger evidence than directory names or aggregate counts. If metadata omits target ID, limit the claim to artifact-set evidence.

## 8. Run gates without contaminating authority state

Materialize an isolated archive of pinned HEAD, overlay only the candidate lock, and run full tests, format, lint, compile, configuration/artifact tests, package build, and diff check there. Delete the temporary tree afterward. This avoids repository build residue and keeps mutation-capable tests away from the live target.

## Decision shape

Report separately:

- `SPEC COMPLIANCE PASS/FAIL`;
- `TASK QUALITY PASS/FAIL`;
- blocking and non-blocking findings;
- `SAFE TO COMMIT/PUSH YES/NO`;
- safety of post-push target-scoped plan/apply/verify/status.

A safe hash-only repair normally requires unchanged authority, only intended hash replacements, unchanged immutable selectors, pristine/generated/live equality, a no-mutation target plan, converged status, clean transaction residue, and fresh gates.
