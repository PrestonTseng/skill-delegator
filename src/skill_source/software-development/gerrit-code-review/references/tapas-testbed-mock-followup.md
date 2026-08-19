# TAPAS testbed mock review follow-up

Use this reference when reviewing or addressing Gerrit comments on `tapas-testbed` mock ADS / mock TriOps services.

## Source-of-truth protocol check

Before changing TAPAS wire enums, inspect the current TAPAS ICD rather than copying a local model assumption.

For current Type 13 TriOps block occupancy, the ICD enum is:

```text
Occupied = 0
Free = 1
```

A useful regression test should decode the packed MsgPack Type 13 payload and assert actual wire values, not just assert the Python enum members.

## Compose review comments: direct configuration

When a reviewer asks that testbed mocks be configured directly rather than through environment variables:

1. Replace the relevant interpolation in `docker-compose.yml` with literal values.
2. Remove obsolete variables from `.env.example`.
3. Update README statements that describe those variables as configurable.
4. Render with `docker compose --env-file .env.example config` and assert the removed variable names are absent while literal values appear in the rendered service environments.

Do not generalize this to host port mappings: retaining variables for port collision avoidance is a separate concern unless explicitly requested otherwise.

## Follow-up validation

After a Type 13 encoding change, run:

- mock TriOps focused and full tests;
- Ruff and compile checks;
- rendered compose verification;
- mock TriOps image build.

When an amd64 Windows testbed is part of the accepted validation path, rebuild/load the Linux/amd64 mock image and rerun the core compose smoke test. Verify Thalos/Unicorn/Crystal requested image versions, mock ADS Safety Server WebSocket connection, mock health endpoints, occupancy mutation/readback, and cleanup.
