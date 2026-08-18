# Source Update Workflow

Source updates and target changes are separate operations.

## 1. Observe Source Changes

```console
skillctl update --check --config my-config
```

For a Git source, this command compares the tracked reference. For a filesystem source, it compares the complete tree identity.

The command can update ignored cache observations. It does not write the lock or change a target.

Exit status 0 means no change. Status 1 means that a change exists. Status 3 means that the operation is unavailable or blocked.

## 2. Propose an Exact Lock

Propose an update for one source:

```console
skillctl update shared --json --config my-config
```

Propose updates for all sources:

```console
skillctl update --all --json --config my-config
```

The command resolves exact revisions and builds a complete candidate lock.

It reports changed hashes, removed skills, renamed skills, and new ungranted skills. Missing pool or grant entries block publication.

The command writes only `skill-lock.yaml`. It does not change targets.

Use `skillctl lock` for an initial lock or an intentional full relock.

## 3. Review and Commit

Review these items:

1. Review each old and new exact source identity.
2. Review each changed skill hash in the pool and grants.
3. Review removed, renamed, new, and ungranted skills.
4. Review `git diff -- my-config/skill-lock.yaml`.
5. Run `skillctl resolve --json --config my-config`.
6. Run `skillctl plan --json --config my-config`.

Commit the accepted lock with your normal Git process.

The CLI does not stage, commit, push, merge, or open a pull request.

## 4. Apply the Accepted State

```console
skillctl validate --config my-config
skillctl plan --json --config my-config
skillctl apply --config my-config
skillctl verify --config my-config
skillctl status --json --config my-config
```

If the reviewed plan contains REMOVE, use `skillctl apply --yes --config my-config`.

`apply` rebuilds the plan from the current configuration and target state. It rejects stale or hostile state.

`verify` hashes each complete cached source snapshot. It also checks ungranted content against the exact lock.

## Test Safety

CAUTION: Do not run generic pytest directly with a real authority configuration at repository-root `config/`.

The pytest session guard accepts only the exact checked-in safe example. It stops before test collection when the root configuration differs.

For engine acceptance, export the engine to an isolated directory. Restore the checked-in safe example before you run the generic tests.

## Rollback Model

Before the manager-record commit boundary, the reconciler keeps backups. It restores exact manager-owned links and records when restoration is safe.

The rollback does not erase an unmanaged object that another process replaced.

After all target manager records are published, the apply is committed. Inspect and clean residual transaction directories after an explicit review.

The lock has a separate commit boundary at its atomic replacement. The tool does not restore the prior lock automatically.

To restore an older lock, restore its reviewed bytes from Git. Then run `plan`, `apply`, and `verify`.

## Runtime Restart

No command restarts another process.

If a consumer reads skills only at startup, restart it after successful verification. Use the runbook for that consumer.
