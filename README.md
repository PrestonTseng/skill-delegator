# skill-delegator

`skill-delegator` is a declarative, fail-closed CLI for publishing a reviewed set of skills as deterministic symlinks. One invocation operates on exactly one authority configuration. It locks mutable source declarations to immutable identities, resolves grants inside that authority's pool, plans changes, transactionally reconciles manager-owned links, and writes content-addressed verification receipts.

V1 is symlink-only and currently targets Python 3.12+ on POSIX systems with `fcntl`, descriptor-relative filesystem operations, and `/proc` descriptor paths (the verified release environment is Linux). It is not a filesystem sandbox.

## Safe quick start

The checked-in `main-example` reads `tests/fixtures/example-source` and may write only below ignored `var/`: source cache, example targets, and receipts. It never names a real agent profile.

```console
uv sync --locked --python 3.12
uv run --frozen skillctl validate
uv run --frozen skillctl lock
uv run --frozen skillctl resolve --json
uv run --frozen skillctl plan --json       # exit 1 means reviewed changes exist
uv run --frozen skillctl apply             # add --yes only when REMOVE is reviewed
uv run --frozen skillctl verify
uv run --frozen skillctl status --json
```

The first `plan` normally exits 1; after `apply`, it exits 0. Repeated `lock`, `apply`, and `verify` converge: the lock bytes remain stable, apply reports `Already converged`, and identical verification evidence reuses the same receipt path.

Use another authority directory with `--config path/to/config`. Review all five files and the plan before apply.

## Commands and exit codes

| Command | Purpose | Exit codes |
|---|---|---|
| `validate` | Schema and authority-policy validation; no source/target creation | 0 valid, 2 invalid |
| `lock` | Resolve sources into ignored cache and atomically publish the exact lock | 0 success, 2 failure |
| `resolve --json` | Pure desired-state resolution | 0 success, 2 failure |
| `plan [--json]` | Read-only current-state scan and reconciliation plan | 0 converged, 1 changes, 3 blocked |
| `apply [--yes]` | Rebuild and transactionally apply the current plan | 0 success, 2 input error, 3 blocked, 4 REMOVE not confirmed, 5 transaction error |
| `verify` | Fresh verification and content-addressed receipt publication | 0 converged, 1 drift, 2 input error, 3 invalid/publication blocked |
| `status [--json]` | Fresh read-only verification without receipt publication | 0 converged, 1 drift, 2 input error, 3 invalid |
| `update --check` | Refresh ignored source observations and compare to lock | 0 unchanged, 1 update observed, 3 unavailable/blocked |
| `update SOURCE|--all` | Validate and publish a candidate exact lock only | 0 success, 3 blocked |

Argument-parser misuse exits 2. CLI diagnostics are bounded at security-sensitive update boundaries, but operators should still treat configured paths as potentially sensitive.

## Authority and branch model

There is no global authority graph. A Preston→Niles configuration and a Niles→worker/reviewer configuration are independent domains, even when they use the same engine repository. Each invocation reads one `config/`; it cannot infer or change another authority's pool or grants.

A typical repository keeps the generic engine and safe example on `main`, while independently reviewed authority configurations may live on separate long-lived branches. Engine updates enter each authority branch only by an explicit human-reviewed Git workflow. The CLI never commits, pushes, merges, opens PRs, or restarts a runtime.

## Test safety for contributors

Generic pytest mutation tests may run only in a tree whose repository-root `config/` is the
checked-in `main-example` with `fixture_policy: safe-main-example`. The session guard aborts
pytest before collection/test bodies when root config is unreadable, malformed, authority-owned,
points outside repository fixture/generated roots, or escapes through an existing symlink
ancestor. Mutation tests that copy root config must use `tests.fixture_safety`; it rewrites every
source and target into the current `tmp_path` and rechecks source, cache, target, and receipt roots
immediately before `lock`, `update`, `apply`, or `verify`.

Never run generic pytest directly on an authority branch. Verify an authority integration by
exporting the accepted engine to an isolated tree, restoring the accepted safe example config,
and running generic tests there. Authority config itself is limited to the separately authorized,
read-only or deployment-specific review workflow; a generic test suite is not an authority
verification mechanism.

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration reference](docs/configuration.md)
- [Update/review/apply workflow](docs/update-workflow.md)
- [Threat model and limits](docs/threat-model.md)
- [Checked-in example notes](config/README.md)

## Non-goals

V1 has no server, database, web UI, target-adapter abstraction, remote deployment, global authority hierarchy, source-trust decision, automatic Git operation, automatic runtime restart, or general filesystem sandbox. It preserves unmanaged target content but does not make untrusted local processes harmless.
