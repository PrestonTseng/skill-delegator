# Contributing

Keep changes small and focused.
Do not add real authority paths, credentials, tokens, private keys, or other secrets.
Use only the safe example on the generic branch.

Run these commands from the repository root:

```console
uv sync --locked --python 3.12
uv run --frozen --python 3.12 pytest -q
uv run --frozen --python 3.12 ruff format --check .
uv run --frozen --python 3.12 ruff check .
uv run --frozen --python 3.12 python -m compileall -q src tests
uv run --frozen --python 3.12 skillctl validate
uv run --frozen --python 3.12 pytest -q tests/integration/test_schema_artifacts.py
uv build --python 3.12
```

Review the complete diff before you submit a change.
