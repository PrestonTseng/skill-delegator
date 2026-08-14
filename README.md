# skill-delegator

A declarative, fail-closed CLI for validating skill delegation configuration.

Task 1 provides configuration validation only. Source discovery, locking, target adapters, and
reconciliation are intentionally outside this foundation.

## Quick start

```console
uv sync
uv run skillctl validate
```

The checked-in example reads only `tests/fixtures/example-source` and resolves target roots below
the Git-ignored `var/example-targets/` directory. Validation does not create those target directories.

Use another configuration directory with:

```console
uv run skillctl validate --config path/to/config
```
