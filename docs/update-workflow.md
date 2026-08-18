# Source Update Workflow

Source updates and target changes are separate operations.

The commands below use a source checkout that was installed with `uv sync`.

## 1. Observe Source Changes

```console
uv run --frozen --python 3.12 skillctl update --check --config my-config
```

For a Git source, this command compares the tracked reference. For a filesystem source, it compares the complete tree identity.

The command can create the cache root and temporary Git checkout data. It does not publish immutable snapshots, write the lock, or change a target.

Exit status 0 means no change. Status 1 means that a change exists. Status 3 means that the operation is unavailable or blocked.

## 2. Propose an Exact Lock

Propose an update for one source:

```console
uv run --frozen --python 3.12 skillctl update shared --json --config my-config
```

Propose updates for all sources:

```console
uv run --frozen --python 3.12 skillctl update --all --json --config my-config
```

The command resolves exact revisions and builds a complete candidate lock.

It can write immutable cache snapshots and `skill-lock.yaml`. It does not change targets.

The output reports valid authority-relevant hash changes and new ungranted skills.

A missing pooled or granted skill blocks the proposal before detailed output. The command reports a bounded `candidate-invalid` error.

Use `uv run --frozen --python 3.12 skillctl lock --config my-config` for an initial lock or an intentional full relock.

## 3. Review and Commit

Review these items:

1. Review each old and new exact source identity.
2. Review each changed skill hash in the pool and grants.
3. Review new and ungranted skills in valid proposal output.
4. Resolve each `candidate-invalid` error before publication.
5. Review `git diff -- my-config/skill-lock.yaml`.
6. Run `uv run --frozen --python 3.12 skillctl resolve --json --config my-config`.
7. Run `uv run --frozen --python 3.12 skillctl plan --json --config my-config`.

Commit the accepted lock with your normal Git process.

The CLI does not stage, commit, push, merge, or open a pull request.

## 4. Apply the Current State

```console
uv run --frozen --python 3.12 skillctl validate --config my-config
uv run --frozen --python 3.12 skillctl plan --json --config my-config
uv run --frozen --python 3.12 skillctl apply --config my-config
uv run --frozen --python 3.12 skillctl verify --config my-config
uv run --frozen --python 3.12 skillctl status --json --config my-config
```

`apply` does not consume the displayed `plan` output. It recomputes and immediately executes a new plan from the current state.

CAUTION: `--yes` authorizes each REMOVE in this new plan. V1 has no plan digest or approved plan-file input.

`apply` rejects stale or hostile state that its fresh checks detect. It never follows a mutable `track` value.

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
