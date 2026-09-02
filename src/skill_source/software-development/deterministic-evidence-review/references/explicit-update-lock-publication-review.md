# Explicit Update Checks and Candidate-Lock Publication

Use this review pattern for CLIs that compare mutable source selectors with exact locks and may publish a replacement lock without applying target state.

## Read-only check boundary

Snapshot config files, lock bytes and inodes, target trees, receipts, Git `HEAD`, index tree (`git write-tree`), staged diff, and worktree status before `update --check`; compare all after. The only permitted write is the declared ignored source cache.

Do not accept a leaf-only `lstat()` check for cache confinement. A cache such as `project/var/cache/sources` can have a regular final directory while `project/var` is a symlink to a configured target or external tree. Probe the real CLI by replacing an existing cache ancestor with a directory symlink and require failure with no target/external entries created. Safe creation walks every existing ancestor with `lstat` or uses retained no-follow directory descriptors.

## Exact selector binding and relation truth

Separate observation from resolution:

1. Resolve the mutable selector to an exact commit/tree.
2. Inventory only that exact identity.
3. Recompare the inventoried identity with the checked identity.
4. Publish only after the complete candidate lock validates.

Race a Git branch forward after check but before inventory: the candidate must retain the checked commit. Race a filesystem source after check: it must either lock the exact checked tree or block as changed. For ancestry labels, an absent old commit is not proof of divergence or force movement when clone depth/object availability is uncertain; return an explicit unknown/unavailable relation unless ancestry is proven. Moved tags should be labeled as tag movement without implying commit ancestry.

## Complete candidate and `--all`

Reject duplicate/corrupt old source identities and exact source-set mismatch before lookup. Preserve every unselected `LockedSource` exactly. Validate all pool and grant references against the complete candidate. For `--all`, fold each successful candidate into the next source's validation, retain coherent per-source old/new evidence, and call the publisher once only after every source succeeds.

Review output must remain hash-only and bounded: canonical ID, old/new hash, and status for governed artifacts; list new ungranted artifacts without granting them; do not emit bodies, source locations, credentials, or raw exceptions.

## Publication fault matrix

Fault-inject every phase of the real lock writer, especially after `os.replace` and during containing-directory `fsync`. A test that monkeypatches the whole writer to fail before it runs does not cover publication semantics.

Record both the return/error and public lock bytes/inode. If `os.replace` succeeds and directory `fsync` fails, a naive writer may report “blocked” while the new lock is already public. The contract must define and enforce one truthful outcome: either rollback to the old identity before reporting failure, or report the publication as installed-with-durability-uncertain rather than claiming no publication. Cleanup errors must not mask the primary failure.

Fault-inject the rollback operation itself, not only the fault that triggers rollback. In the existing-target case, combine a post-publication directory-`fsync` failure with failure of the backup-to-public `os.replace`; in the initially-absent case, combine it with failure of the rollback `unlink`. A generic `lock-publication-failed` result is contradictory if the candidate remains public. The implementation must either restore the exact prior inode/absence before returning a blocked result, or surface an explicit rollback-unsafe/installed-uncertain outcome while preserving any identity-verified recovery journal. Committed regression tests must assert the public bytes, inode, journal state, and exact safe code for both compound failures.

## Minimal acceptance evidence

- Focused check/update tests and full suite pass.
- Human and JSON bytes are deterministic for identical inputs.
- No apply/stage/commit/push/merge call is reachable from update paths.
- `--check` leaves protected bytes, inodes, targets, receipts, and Git state unchanged.
- Selector races bind exact identities or fail closed.
- Cache-ancestor symlink probe fails without external mutation.
- Every candidate validates complete authority before one lock-only publication.
- Post-replace publication faults produce a truthful, contract-consistent public outcome.
