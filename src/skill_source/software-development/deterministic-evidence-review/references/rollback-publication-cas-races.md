# Rollback Publication Compare-and-Swap Races

Use this probe when a filesystem publisher classifies a public pathname by inode and bytes, then tries to restore a backup or prior absence after a post-publication error.

## The hidden race

A pre-rollback observation is not authorization for a later destructive pathname operation:

```text
observe public path == staged candidate inode+bytes
→ concurrent actor replaces public path
→ unconditional backup-to-public replace or public unlink
```

The rollback can overwrite or delete the concurrent entry, then re-observe an apparently safe prior state and return the original bounded failure. Tests that race only **before** classification or during the subsequent directory `fsync` do not reach this checkpoint.

This is a TOCTOU defect even when all access is descriptor-relative and no-follow. Retaining the parent directory descriptor confines the pathname but does not make `unlink` or `rename` conditional on the leaf inode previously observed.

## Deterministic probe matrix

Inject the concurrent replacement inside the rollback syscall shim, immediately before forwarding to the real operation:

1. **Prior file existed**
   - Trigger a post-publication directory-fsync error.
   - Let candidate observation succeed.
   - On backup-to-public `replace`, first install a same-candidate-bytes/new-inode concurrent file at the public name.
   - Record its inode, then forward the rollback `replace`.
   - Require the concurrent inode to remain public and the call to raise `lock-rollback-unsafe`.

2. **Prior path was absent**
   - Trigger the same post-publication error.
   - Let candidate observation succeed.
   - On rollback `unlink`, first replace the public candidate with a new concurrent inode.
   - Require that inode to remain public and the call to raise `lock-rollback-unsafe`.

Repeat with different bytes, a symlink, a non-regular leaf, and a missing leaf where applicable. Record return/error, bytes, inode/type, and backup-journal state. Never accept a passing test unless it proves the injection checkpoint was reached.

## Acceptance rule

The destructive rollback operation must be coupled to the candidate identity, not merely preceded by an identity check. If the platform/API cannot provide an inode-conditional remove/replace primitive, use a design that makes ownership exclusive or changes the public contract so rollback never destroys a pathname that could have changed concurrently. A final re-observation can classify the damage but cannot undo an unsafe overwrite or deletion.

Safe outcomes remain:

- exact prior inode and bytes, or exact prior absence: report the original bounded failure;
- exact staged candidate inode and bytes still public: return success and emit the normal publication result;
- every other state: preserve it and raise the bounded rollback-unsafe result;
- cleanup backup journals best-effort only after the public outcome is known safe, without changing that outcome.
