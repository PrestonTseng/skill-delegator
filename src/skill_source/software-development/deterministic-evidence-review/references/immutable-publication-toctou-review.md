# Immutable Publication TOCTOU Review

Use this reference when a deterministic evidence CLI stages files and atomically publishes a directory. Atomic no-overwrite rename is necessary but not sufficient: the success path, verification path, and rollback path must all remain bound to the same filesystem objects.

## Threat model

Assume another same-UID process can replace names or ancestors between checks. A prior `lstat()`, `is_symlink()`, or `resolve()` does not authorize later pathname operations. The safe unit is a retained descriptor plus `(st_dev, st_ino)` identity.

## Required state machine

### 1. Bind source identity

- Require the supplied root to equal `git rev-parse --show-toplevel` exactly.
- Verify the executing package/module files reside under that root and match the recorded commit tree.
- Read each governed config once. Hash and interpret those exact bytes; do not hash one read and parse another.
- Prefer immutable byte snapshots such as sealed memfds when existing path-only loaders must consume the snapshot.
- Recheck HEAD, module bytes, and governed config identity immediately before publication.

### 2. Traverse and create by descriptor

- Walk ancestry with retained `O_DIRECTORY | O_NOFOLLOW` descriptors.
- Create descendants with `dir_fd`; fsync every parent whose directory entry changed and each new directory.
- Pass writable cache roots through a stable fd path such as `/proc/self/fd/<fd>` only when the platform and loader support it.
- Treat every opened child as owned immediately. If `fstat`, permission repair, or `fsync` fails, close that child before propagating the primary error.

### 3. Stage durably

- Take cleanup ownership immediately after staging `mkdir`, before parent fsync or staging open.
- Create files with `O_CREAT | O_EXCL | O_NOFOLLOW`, write all bytes, flush/fsync, and fsync the staging directory.
- Keep the staging directory fd open across publication.

### 4. Publish and rebind the public name

- Publish with same-parent kernel no-replace semantics (`renameat2(RENAME_NOREPLACE)` or a proved equivalent).
- Fsync the parent directory.
- Nofollow-open the final public name relative to the retained parent fd.
- Compare the rebound fd's `(st_dev, st_ino)` with the retained staging/publication fd. A mismatch is failure.
- Perform final verification through the rebound public-name fd, not merely through the pre-rename staging fd.

### 5. Verify the exact artifact set through opened fds

- Enumerate the rebound final directory and require the exact expected names—no extras.
- For each name: `open(..., O_NOFOLLOW)` first, then immediately `fstat()` that opened fd and require `S_ISREG` before reading.
- Do not use `stat(name)` followed by a separate `open(name)`; that is a type-substitution race.
- Read/hash every expected artifact from its verified fd. Check canonical bytes and terminal-newline rules before emitting success.

### 6. Roll back without deleting replacements

- Preserve the primary publication/verification exception; cleanup errors become notes or chained diagnostics.
- Before rollback, confirm the current public name still identifies the retained publication inode.
- Move it to a unique quarantine name with no-replace semantics, fsync the parent, nofollow-open quarantine, and recheck inode identity.
- Delete only while the quarantined directory and each opened child remain descriptor-bound and type-checked. Never recursively delete a name whose identity changed.
- If identity cannot be proved, leave the foreign replacement untouched and fail without success output.
- Fsync quarantine creation/removal and final parent state.

## Minimum adversarial fault matrix

1. Child-directory fsync after open (prove fd closure).
2. Staging parent fsync and staging open immediately after mkdir (prove residue cleanup).
3. Publish rename collision and kernel primitive unavailable.
4. Parent fsync after successful rename.
5. Final public-name replacement before rebound open.
6. Public-name inode mismatch after rebound open.
7. Extra final entry, symlink entry, FIFO/device/directory entry.
8. Artifact substitution between enumeration and open (prove opened-fd `fstat` rejection).
9. Read/hash mismatch after rename.
10. Quarantine rename collision/failure, quarantine fsync failure, quarantine identity replacement, and deletion failure.
11. Cleanup failure while another primary exception is active.
12. Root/Git/module mismatch and concurrent config drift.
13. Boolean-as-integer schema values.
14. Actual `python -m ...` success and failure behavior, including zero success JSON on failure.

For every post-rename failure, assert no CLI-owned successful destination remains. For race substitutions, also assert unrelated replacements are not deleted.

## Approval rule

Do not approve immutable publication while any success path can verify one inode but report another pathname, while artifact type is checked before rather than after open, or while rollback can recursively delete an unverified name. Deterministic bytes and passing happy-path tests do not compensate for these evidence-integrity defects.
