# Contributing

Thank you for contributing to `skill-delegator`.

Keep each change small and focused. Use generic examples in public documents and tests.

Do not add real authority paths, credentials, tokens, private keys, or other secrets.

## Development Setup

```console
git clone https://github.com/PrestonTseng/skill-delegator.git
cd skill-delegator
uv sync --locked --python 3.12
```

## Required Checks

Run these commands from the repository root:

```console
uv run --frozen --python 3.12 pytest -q
uv run --frozen --python 3.12 ruff format --check .
uv run --frozen --python 3.12 ruff check .
uv run --frozen --python 3.12 python -m compileall -q src tests
uv run --frozen --python 3.12 skillctl validate
uv run --frozen --python 3.12 pytest -q tests/integration/test_schema_artifacts.py
uv build --python 3.12
```

Review the complete diff before you submit a change.

If you change behavior, add a focused test that fails without the change.

Authority branches use `fixture_policy: none` and must not run generic tests directly. Generic engine tests use the checked-in safe example from `main`; see the [configuration reference](docs/configuration.md).

## Pull Requests

Explain the problem, the change, and the verification results.

Keep generated caches, targets, transaction data, receipts, and build artifacts out of the commit.
