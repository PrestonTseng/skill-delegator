# Update, review, and apply workflow

Source update and target deployment are deliberately separate.

## 1. Observe

```console
skillctl update --check --config config
```

For Git this refreshes/compares the tracked ref; for filesystem sources it compares tree identity. It may mutate ignored cache observations, but it does not write the lock, pool, grants, targets, Git index/history, commits, pushes, merges, PRs, or runtime state. Exit 0 means no change, 1 means a difference was observed, and 3 means unavailable/blocked.

## 2. Propose an exact lock

```console
skillctl update shared --json --config config
# or, deliberately:
skillctl update --all --json --config config
```

The command resolves exact revisions, rebuilds and validates the complete candidate, reports authority-relevant artifact hash changes plus ungranted additions/removals, and atomically publishes only `skill-lock.yaml`. Missing pool/grant references block publication. An update command does not apply targets.

`skillctl lock` is the explicit full relock operation and has the same separation from apply. Use it for initial locking or when a full source resolution is intended.

## 3. Review and version

Review:

1. old/new exact source identities (Git commit plus directly locked complete-snapshot tree hash, or filesystem tree hash);
2. every pooled/delegated artifact hash change;
3. removed/renamed artifacts and new ungranted artifacts;
4. the complete `git diff -- config/skill-lock.yaml`;
5. `skillctl resolve --json` and `skillctl plan --json`.

Then use your normal human-controlled Git process to commit the lock. The CLI does not commit, stage, push, merge, or open a PR. Independent authority branches review and accept engine/config updates independently.

Generic pytest is not safe authority-config verification and must never be invoked directly in an
authority branch. For engine acceptance, export the accepted engine commit into an isolated tree,
restore the checked-in generic `main-example` config and fixture, and run pytest there. The
repository pytest session guard intentionally rejects authority root config before any test body.

## 4. Apply the reviewed exact state

```console
skillctl validate --config config
skillctl plan --json --config config
skillctl apply --config config        # --yes if and only if reviewed REMOVE exists
skillctl verify --config config
skillctl status --json --config config
```

Apply reconstructs desired/current state from current config and lock, locks targets, and rejects stale or hostile state. It never follows `track`. Verify independently freshly hashes each complete cached source snapshot once, checks that identity against the lock even for ungranted content, and writes a content-addressed receipt containing the Git commit plus snapshot hash (or filesystem snapshot hash).

## Rollback model

Before the apply metadata commit boundary, the reconciler retains backups and restores exact manager-owned links/metadata when safe. It never removes a concurrently replaced unmanaged object merely to force rollback. A rollback failure is surfaced and bounded failure evidence may remain on pre-existing targets.

After all target `managed.json` publications complete, apply is committed. Cleanup failures are reported as committed; operators should verify and clean residual manager transaction directories deliberately rather than assume rollback.

The lock's atomic `os.replace` is its commit boundary. No automatic old-lock rollback occurs after replace. Review/version control is the durable way to restore an older accepted lock: restore reviewed lock bytes in Git, plan, explicitly apply, and verify.

No command restarts a worker or other runtime. If a consumer only discovers skills at startup, restart it manually after successful verification according to that consumer's runbook.
