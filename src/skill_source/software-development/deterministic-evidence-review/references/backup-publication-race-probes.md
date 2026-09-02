# Backup publication race probes

Use this when a backup command validates a temporary SQLite copy and atomically replaces a public target. A happy-path online-backup test and one injected `fsync` failure do not establish safe publication.

## Pin the exact executable snapshot

For staged work, export the index to an isolated directory and run every probe there. At capture time, save all three values separately:

```bash
review_tree=$(git write-tree)
git diff --cached --binary >"$evidence_dir/review.diff"
review_diff_sha256=$(sha256sum "$evidence_dir/review.diff" | cut -d' ' -f1)
review_base=$(git rev-parse HEAD)
```

Do not later recompute `git diff --cached` and label its hash as the reviewed digest: the index may have been committed, making the new digest the empty-stream SHA. If the index becomes empty, require `git rev-parse HEAD^{tree}` to equal `review_tree`, identify the concurrent commit, and retain the saved non-empty diff digest as the reviewed-delta identity.

## Required race matrix

### Existing target

Pause publisher A after it moves the old target to its rollback pathname, then start publisher B. B must not interpret the in-progress rollback as an ordinary stale file or mutate either target. After both finish, exactly one coherent outcome must be attributable to each return value.

### Initially absent target

Synchronize two publishers after both have observed the target as absent but before publication. Without serialization, both can return success while the later replace overwrites the earlier result. Hash the final public bytes and compare them independently with every successful call's returned digest. A successful call whose digest no longer identifies the public target is a reproduced race, even when no temporary residue remains.

Preferred remediation is a cross-process target-scoped lock covering target-state inspection, publication, directory durability, rollback cleanup, and result construction. A process-local lock is insufficient for CLI invocations.

## Cleanup-failure precedence

Inject a primary failure after the new target is installed, such as containing-directory `fsync`, then inject a rollback failure. Verify all of the following:

- the primary exception remains the raised exception;
- cleanup failure is attached as a note/diagnostic and does not mask it;
- the exact public target and rollback path state is reported;
- future calls fail closed on recoverable residue;
- temporary SQLite `-wal` and `-shm` sidecars are cleaned.

A narrow test that injects only the primary failure misses exception masking and split-brain recovery states.

## Lineage analogue for storage snapshots

For append-only versioned snapshots, adjacency plus final-watermark checks do not prove complete lineage. Delete the first inherited mapping for one symbol while leaving later rows contiguous, then commit a valid overlapping increment. Require rejection, or prove every symbol retains the same expected inherited start and range. Also run two writers against the same base; exactly one may advance the latest lineage and the loser must roll back without new committed mappings.
