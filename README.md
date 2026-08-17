# skill-delegator

## What the tool does

`skill-delegator` publishes a reviewed set of skills as deterministic symlinks.
It reads one authority configuration in each invocation.
It fails closed when an input or boundary is invalid.

The tool locks mutable source declarations to exact source identities.
It resolves grants inside the authority pool.
It compares the desired state with the current targets.
It applies reviewed changes to manager-owned links.
It writes content-addressed verification receipts.

V1 requires Python 3.12 or later on POSIX.
The verified release environment is Linux.
V1 uses `fcntl`, descriptor-relative filesystem operations, and `/proc` descriptor paths.

## Safety boundary

V1 creates symlinks only.
It is not a filesystem sandbox.
It preserves unmanaged target content.
It does not make untrusted local processes safe.

One invocation uses exactly one authority configuration.
The engine has no global authority hierarchy.
It cannot infer another authority pool or grant.
It cannot change another authority domain.

`apply` is the only command that reconciles targets.
A REMOVE operation requires a valid manager record.
A REMOVE operation also requires `--yes`.
Do not add `--yes` unless a human reviewed each REMOVE operation.

The tool does not select trusted source content.
The owner must decide whether each source is safe to delegate.

The CLI never commits, pushes, merges, or opens a pull request.
The CLI never restarts a worker or another runtime.
Configuration edits do not automatically apply in V1.
The engine never starts the next authority invocation.

## Install and test the safe example

The `main` branch contains only the generic engine, generic documents, and the safe example.
Niles maintains only the generic tool on `main` and the Simple English documents.
The safe example does not name a real agent profile.

The safe example reads `tests/fixtures/example-source`.
It writes generated data only below ignored `var/cache/`, `var/example-targets/`, and `var/receipts/`.

Run these commands from a clean generic checkout:

```console
uv sync --locked --python 3.12
uv run --frozen --python 3.12 pytest -q
uv run --frozen --python 3.12 skillctl validate
uv run --frozen --python 3.12 skillctl lock
uv run --frozen --python 3.12 skillctl resolve --json
uv run --frozen --python 3.12 skillctl plan --json
uv run --frozen --python 3.12 skillctl apply
uv run --frozen --python 3.12 skillctl verify
uv run --frozen --python 3.12 skillctl status --json
```

The first `plan` normally exits 1 because it finds CREATE operations.
After `apply`, `plan` exits 0.
A repeated `lock` keeps the same lock bytes for the same source state.
A repeated `apply` reports `Already converged`.
Identical verification evidence uses the same receipt path.

CAUTION: Never replace the safe example on `main` with real authority paths.
Real source and target paths belong only in an authority branch that its owner accepts.

## The five configuration files

Each authority configuration contains exactly five YAML files.
Each file uses `schema_version: 1`.
The schemas reject unknown fields and duplicate YAML keys.

For the Preston→Niles authority, Preston alone writes and accepts the desired state.
Niles must not author the Preston desired state.
Niles can review the generic engine and these generic documents.

| File | Purpose | Owner for Preston→Niles |
|---|---|---|
| `authority.yaml` | Names the authority and requires `fail_closed: true`. | Preston writes and accepts it. |
| `sources.yaml` | Declares reviewed Git or filesystem sources. | Preston writes and accepts it. |
| `pool.yaml` | Sets the maximum set that this authority can delegate. | Preston writes and accepts it. |
| `delegations.yaml` | Declares targets and grants from the pool. | Preston writes and accepts it. |
| `skill-lock.yaml` | Records exact source, tree, skill, path, and content identities. | The tool generates it. Preston reviews and accepts it. |

The pool is a delegation ceiling.
A lock operation does not add discovered skills to the pool.
Each grant must be in the pool and the exact lock.

## Create an authority branch and configuration

Keep generic `main` free of real authority paths.
Create a separate long-lived branch from the accepted generic commit.
Use a branch that has one named authority owner.

Set `AUTHORITY_BRANCH` to the accepted branch name.
Then create the branch:

```console
git switch main
git switch -c "$AUTHORITY_BRANCH"
```

On that branch, replace the safe example with the authority configuration.
Do not first add real paths to `main`.
Do not copy accepted authority files back to `main`.

For Preston→Niles, Preston writes the four desired-state files.
Then Preston generates `skill-lock.yaml` with `lock`.
Preston reviews all five files before acceptance.
Preston uses the normal human-controlled Git process to commit them.

If the configuration is not in repository-root `config/`, use `--config path/to/config`.
Run only one configuration directory in each invocation.

The commands have these write boundaries:

- `validate` reads the configuration and creates no source or target.
- `lock` writes only the exact lock and the ignored source cache.
- `resolve` reads desired state and does not write a target.
- `plan` reads current state and does not write a target.
- `update` writes only source observations and the candidate exact lock.
- `apply` is the only target-reconciliation command.
- `verify` reads fresh evidence and can publish a receipt.
- `status` reads fresh evidence and does not publish a receipt.

## Authority operation workflow

Use this exact order for a new or changed authority configuration:

```text
validate → lock → resolve → plan → human review/commit → apply → verify → status
```

Run the commands on the authority branch:

```console
skillctl validate --config config
skillctl lock --config config
skillctl resolve --json --config config
skillctl plan --json --config config
```

Review the complete plan.
Review each CREATE, REPLACE, REMOVE, and KEEP operation.
Review `git diff -- config/`.
Commit only the accepted configuration and exact lock.

Apply the committed state only after the human review:

```console
skillctl apply --config config
skillctl verify --config config
skillctl status --json --config config
```

If the reviewed plan contains REMOVE, use this command instead:

```console
skillctl apply --yes --config config
```

Do not use an old plan as approval for changed files.
`apply` rebuilds the plan from the current configuration and target state.
It rejects stale or hostile state.

If a consumer reads skills only at startup, restart it after successful verification.
Use the runbook for that consumer.
The CLI does not do this restart.

## Expected exits

Argument-parser misuse exits 2.
Treat configured paths in diagnostics as sensitive information.

| Command | Exit | Meaning |
|---|---:|---|
| `validate` | 0 | The configuration is valid. |
| `validate` | 2 | The configuration is invalid. |
| `lock` | 0 | The exact lock and ignored source cache are ready. |
| `lock` | 2 | The lock operation failed. |
| `resolve --json` | 0 | Desired-state resolution succeeded. |
| `resolve --json` | 2 | Desired-state resolution failed. |
| `plan [--json]` | 0 | The targets are converged. |
| `plan [--json]` | 1 | The plan contains changes. |
| `plan [--json]` | 3 | The plan is blocked. |
| `apply [--yes]` | 0 | The apply operation succeeded. |
| `apply [--yes]` | 2 | An input error occurred. |
| `apply [--yes]` | 3 | The apply operation is blocked. |
| `apply [--yes]` | 4 | A REMOVE operation lacks confirmation. |
| `apply [--yes]` | 5 | A transaction error occurred. |
| `verify` | 0 | The targets are converged, and the receipt is published. |
| `verify` | 1 | Drift exists. |
| `verify` | 2 | An input error occurred. |
| `verify` | 3 | The state is invalid, or receipt publication is blocked. |
| `status [--json]` | 0 | The targets are converged. |
| `status [--json]` | 1 | Drift exists. |
| `status [--json]` | 2 | An input error occurred. |
| `status [--json]` | 3 | The state is invalid. |
| `update --check` | 0 | The observed source identity is unchanged. |
| `update --check` | 1 | A source update was observed. |
| `update --check` | 3 | The source is unavailable, or the operation is blocked. |
| `update SOURCE|--all` | 0 | The candidate exact lock was published. |
| `update SOURCE|--all` | 3 | The update operation is blocked. |

## Preston→Niles, then Niles→worker/reviewer

Complete the Preston→Niles authority first.
Preston writes and accepts that authority configuration.
Preston applies it to `/opt/data/skills`.
Preston verifies it and gets a successful status.

Only then can Niles inventory the actual `/opt/data/skills` root.
Niles can then create an independent Niles→worker/reviewer authority configuration.
Niles owns the desired state in that downstream authority.
Niles reviews and accepts its five files independently.
Niles then applies and verifies that authority in a separate invocation.

The two authority configurations are independent domains.
The shared engine does not make one configuration the parent of the other.
The engine never invokes the downstream authority after the upstream operation.

An optional future scheduler is outside V1.
Do not design or enable a scheduler before one successful manual end-to-end cycle.
A scheduler must preserve one configuration per invocation and the same human approval boundaries.

## Source update workflow

Source observation and target application are separate operations.
A mutable Git `track` value is an update input.
`apply` never uses `track` as an exact identity.

First, observe available source changes:

```console
skillctl update --check --config config
```

This command can refresh the ignored source cache.
It does not write the lock, targets, Git history, or runtime state.

Then propose an exact lock for one source:

```console
skillctl update shared --json --config config
```

If a full source update is intended, use this command:

```console
skillctl update --all --json --config config
```

The update command validates and publishes only the candidate `skill-lock.yaml`.
It does not apply targets.

Review these items before acceptance:

1. Review each old and new exact source identity.
2. Review each changed artifact hash in the pool and grants.
3. Review removed, renamed, new, and ungranted artifacts.
4. Review `git diff -- config/skill-lock.yaml`.
5. Run `skillctl resolve --json --config config`.
6. Run `skillctl plan --json --config config`.
7. Commit the accepted exact lock with the human-controlled Git process.
8. Run `skillctl apply --config config`.
9. Run `skillctl verify --config config`.
10. Run `skillctl status --json --config config`.

## Test safety

Generic pytest mutation tests can run only with the exact safe example at repository-root `config/`.
The safe configuration uses `authority.id: main-example` and `fixture_policy: safe-main-example`.

The pytest session guard verifies the exact safe-configuration file set and hashes.
The guard stops before collection when the root configuration is not the accepted safe example.
It also rejects paths outside the repository fixture and generated roots.
It rejects escapes through an existing symlink ancestor.

Mutation tests that copy root configuration must use `tests.fixture_safety`.
That helper rewrites each source and target below the current `tmp_path`.
It verifies source, cache, target, and receipt roots before each mutation command.

CAUTION: Never run generic pytest directly on an authority branch.
A generic test suite is not an authority verification method.

For engine acceptance, export the accepted engine to an isolated tree.
Restore the accepted safe example in that isolated tree.
Then run the generic tests there.

If an intentional review changes the accepted safe example, update `SAFE_CONFIG_SHA256` in `conftest.py` in the same commit.
Follow [the safe example instructions](config/README.md) for the exact hash command.
Never add authority-specific paths to the safe manifest.

## Recovery and stop conditions

If `validate`, `lock`, or `resolve` returns a nonzero exit, stop.
If `plan` exits 3, stop.
If the plan contains an unexpected operation, stop.
If the configuration diff contains an unreviewed path or grant, stop.
If any REMOVE operation lacks explicit approval, stop before `apply`.

If `apply` exits 2, 3, 4, or 5, do not start another authority invocation.
Read the bounded diagnostic and inspect the affected target.
Preserve `failure.json` and transaction evidence for review.
Do not remove an unmanaged object to force convergence.
Do not assume that a cleanup error caused a rollback.

If `verify` or `status` returns a nonzero exit, treat the state as not accepted.
Do not restart a runtime.
Do not start the downstream authority invocation.
Correct the cause, and then repeat the manual workflow.

To restore an older lock, restore its reviewed bytes from Git.
Then run `plan`.
Review the complete plan.
Then run `skillctl apply --config config`.
Then run `skillctl verify --config config`.
Then run `skillctl status --json --config config`.
The tool does not automatically restore an old lock after lock publication.

After a committed apply, inspect reported cleanup errors.
Remove residual manager transaction directories only after deliberate review.

## Documentation

- [Architecture and authority scope](docs/architecture.md)
- [Configuration reference](docs/configuration.md)
- [Source update and apply workflow](docs/update-workflow.md)
- [Threat model and limits](docs/threat-model.md)
- [Safe example notes](config/README.md)
