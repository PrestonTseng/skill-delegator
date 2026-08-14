# Configuration

These five files form one authority instance. Every file is validated against a strict JSON Schema;
unknown keys fail validation.

The checked-in `main-example` uses a local fixture source and the `safe-main-example` fixture policy.
That policy rejects absolute target roots and requires every normalized target root to remain below
`var/example-targets/`. `skillctl validate` resolves paths but neither requires nor creates targets.
