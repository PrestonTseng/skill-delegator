# Safe Example Configuration

The `config/` directory contains a complete and safe example.

Use this example to learn the CLI. Do not replace it with real authority paths.

## Files

The example contains these five files:

- `authority.yaml` names the `main-example` authority.
- `sources.yaml` reads `tests/fixtures/example-source`.
- `pool.yaml` permits the `example/hello` skill.
- `delegations.yaml` grants the skill to two example targets.
- `skill-lock.yaml` records the exact source and skill hashes.

All generated paths stay below ignored directories in `var/`.

## Run the Example

Run these commands from the repository root:

```console
uv sync --locked --python 3.12
uv run --frozen --python 3.12 skillctl validate
uv run --frozen --python 3.12 skillctl lock
uv run --frozen --python 3.12 skillctl resolve --json
uv run --frozen --python 3.12 skillctl plan --json
```

The first `plan` exits with status 1 because it contains CREATE operations.

Review the plan. Then apply and verify it:

```console
uv run --frozen --python 3.12 skillctl apply
uv run --frozen --python 3.12 skillctl verify
uv run --frozen --python 3.12 skillctl status --json
uv run --frozen --python 3.12 skillctl plan --json
```

The final `plan` exits with status 0.

## Create a Real Configuration

Copy this directory to a separate configuration directory:

```console
cp -R config my-config
```

Set `fixture_policy: none`. Then replace the example source, pool, target roots, and grants.

Run this command after you change a source:

```console
uv run --frozen --python 3.12 skillctl lock --config my-config
```

This command replaces the example lock with an exact lock for your source.

Read the [README](../README.md) for the complete onboarding procedure. Read the [configuration reference](../docs/configuration.md) for all field rules.

## Update the Safe Example

The test guard protects the exact safe configuration files and hashes.

If an intentional review changes this example, update the guard in the same commit:

1. Finish the reviewed edits to `config/README.md` and the five YAML files.
2. Run `sha256sum` for those six files.
3. Replace the matching values in `SAFE_CONFIG_SHA256` in `conftest.py`.
4. Run `pytest -q tests/integration/test_pytest_safety_guard.py`.

Do not add authority-specific paths to the safe manifest.
