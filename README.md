# skill-delegator

[![CI](https://github.com/PrestonTseng/skill-delegator/actions/workflows/ci.yml/badge.svg)](https://github.com/PrestonTseng/skill-delegator/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

`skill-delegator` publishes reviewed skills to local target directories as deterministic symlinks.

It gives one authority a controlled skill pool. That authority can grant selected skills to one or more targets.

## Why use it?

Use `skill-delegator` when you need these controls:

- Keep skill sources and target grants in versioned YAML files.
- Lock mutable sources to exact Git commits and content hashes.
- Review every target change before it occurs.
- Preserve files and links that the tool does not manage.
- Detect drift and create content-addressed verification receipts.
- Keep each authority configuration independent.

## Requirements

- Python 3.12 or later
- A POSIX operating system
- Git
- [uv](https://docs.astral.sh/uv/)

The verified release environment is Linux. V1 uses `fcntl`, descriptor-relative file operations, and `/proc` descriptor paths.

## Quick Start

The repository includes a safe example. It reads a test skill and writes only to ignored paths under `var/`.

### 1. Clone and install

```console
git clone https://github.com/PrestonTseng/skill-delegator.git
cd skill-delegator
uv sync --locked --python 3.12
```

### 2. Inspect the example configuration

```console
uv run --frozen --python 3.12 skillctl validate
uv run --frozen --python 3.12 skillctl resolve --json
```

The default configuration is in `config/`. It grants one example skill to two example targets.

### 3. Build the plan

```console
uv run --frozen --python 3.12 skillctl lock
uv run --frozen --python 3.12 skillctl plan --json
```

The first `plan` exits with status 1. This status means that the plan contains changes.

Review every `CREATE`, `REPLACE`, `REMOVE`, and `KEEP` operation before you continue.

### 4. Apply and verify the plan

```console
uv run --frozen --python 3.12 skillctl apply
uv run --frozen --python 3.12 skillctl verify
uv run --frozen --python 3.12 skillctl status --json
uv run --frozen --python 3.12 skillctl plan --json
```

The final `plan` exits with status 0. The targets now match the configuration.

A repeated `apply` reports `Already converged`. Identical verification evidence uses the same receipt path.

## Create Your Configuration

Each authority uses one directory with five YAML files.

| File | Purpose | Maintainer |
|---|---|---|
| `authority.yaml` | Names the authority and enables fail-closed behavior. | The authority owner |
| `sources.yaml` | Declares reviewed Git or filesystem sources. | The authority owner |
| `pool.yaml` | Sets the maximum skill set that the authority can grant. | The authority owner |
| `delegations.yaml` | Declares target roots and grants from the pool. | The authority owner |
| `skill-lock.yaml` | Records exact source and skill identities. | `skillctl lock` generates it. The authority owner reviews it. |

All files use `schema_version: 1`. The schemas reject duplicate YAML keys and unknown fields.

### 1. Copy the safe example

Keep real paths out of the generic `config/` directory.

```console
cp -R config my-config
```

### 2. Name the authority

Edit `my-config/authority.yaml`:

```yaml
schema_version: 1
authority:
  id: team-a
  fail_closed: true
  fixture_policy: none
```

### 3. Add a reviewed source

Edit `my-config/sources.yaml`:

```yaml
schema_version: 1
sources:
  - id: shared
    type: git
    location: https://github.com/example/skills.git
    track: main
    skill_root: skills
```

A filesystem source uses `type: filesystem` and does not use `track`.

### 4. Set the authority pool

Edit `my-config/pool.yaml`:

```yaml
schema_version: 1
skills:
  - shared/code-review
```

The pool is a ceiling. Source discovery does not add skills to the pool.

### 5. Add a target and its grants

Edit `my-config/delegations.yaml`:

```yaml
schema_version: 1
targets:
  - id: worker
    root: /srv/agents/worker/skills
    grants:
      - shared/code-review
```

Each grant must exist in both the pool and the exact lock.

### 6. Generate and review the exact lock

```console
uv run --frozen --python 3.12 skillctl lock --config my-config
uv run --frozen --python 3.12 skillctl validate --config my-config
uv run --frozen --python 3.12 skillctl resolve --json --config my-config
uv run --frozen --python 3.12 skillctl plan --json --config my-config
```

Review all five files. Then commit the accepted configuration with your normal Git process.

Read the [configuration reference](docs/configuration.md) before you use advanced paths or multiple sources.

## Safe Operation Workflow

Use this workflow for each new or changed configuration:

```text
lock → validate → resolve → plan → human review and commit → apply → verify → status
```

`lock` changes only `skill-lock.yaml` and the ignored source cache. It does not change a target.

`resolve` and `plan` do not change a target. Use their output to review the desired and current states.

`apply` is the only command that changes targets.

`verify` reads fresh source and target evidence. It can write a content-addressed receipt.

`status` reads fresh evidence without writing a receipt.

### REMOVE operations

CAUTION: Do not add `--yes` until a human reviews every REMOVE operation. A REMOVE can erase a manager-owned link.

If the reviewed plan contains a REMOVE, use this command:

```console
skillctl apply --yes --config my-config
```

The tool preserves unmanaged target content. A REMOVE also requires a valid manager record.

## Command Summary

| Command | Purpose | Target write |
|---|---|---:|
| `validate` | Validate all five configuration files. | No |
| `lock` | Resolve sources and write the exact lock. | No |
| `resolve --json` | Show the desired target state. | No |
| `plan [--json]` | Compare the desired and current states. | No |
| `apply [--yes]` | Apply the current validated plan. | Yes |
| `verify` | Verify fresh evidence and write a receipt. | No |
| `status [--json]` | Report fresh state without a receipt. | No |
| `update --check` | Observe source changes. | No |
| `update SOURCE|--all` | Write a candidate exact lock. | No |

Run `skillctl COMMAND --help` for command options.

## Safety Model

V1 creates symlinks only. It is not a filesystem sandbox or a malware scanner.

One invocation reads one authority configuration. The engine has no global authority hierarchy.

The tool does not select trusted source content. The authority owner must review each source before delegation.

The CLI does not commit, push, merge, open pull requests, or restart another process.

Configuration changes do not apply automatically. The engine also does not start another authority invocation.

Read the [threat model](docs/threat-model.md) before production use.

## Generated State

The tool can create these paths:

- `var/cache/sources/`: immutable source snapshots
- `<target>/.skill-delegator/managed.json`: manager-owned link records
- `<target>/.skill-delegator/`: transaction locks and failure evidence
- `var/receipts/`: content-addressed verification receipts

Do not commit generated caches, targets, transaction data, or receipts as configuration.

## Documentation

- [Configuration reference](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Source update workflow](docs/update-workflow.md)
- [Threat model and security limits](docs/threat-model.md)
- [Safe example notes](config/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

This project uses the [MIT License](LICENSE).
