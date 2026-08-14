# Configuration

These five YAML files form one authority instance. Every document has `schema_version: 1`, is checked against a strict bundled JSON Schema, rejects duplicate YAML keys, and rejects unknown fields.

- `authority.yaml`: one authority ID, mandatory `fail_closed: true`, and fixture policy.
- `sources.yaml`: filesystem or Git source declarations. Git sources require a mutable `track`, but apply never consumes it.
- `pool.yaml`: canonical skill IDs forming this authority's delegation ceiling.
- `delegations.yaml`: target IDs, roots, and non-empty grants. Every grant must be in the pool.
- `skill-lock.yaml`: generated exact source identity, canonical/runtime identity, source-relative path, and content hash.

Canonical IDs are `<source-id>/<path-relative-to-skill-root>`. Runtime names come from `SKILL.md` frontmatter and must be 1–128 ASCII letters, digits, dots, underscores, or hyphens, beginning with a letter or digit. A duplicate runtime name inside one target fails closed.

## Checked-in safe example

`main-example` uses `fixture_policy: safe-main-example`. Its filesystem source is `../tests/fixtures/example-source`; its relative target roots normalize below ignored `../var/example-targets/`. Existing symlinked or non-directory target components are rejected. `validate` reads configuration only. `lock` may create ignored `var/cache`; `apply` creates only configured example targets and manager metadata; `verify` may create ignored `var/receipts`.

Do not replace this policy with real authority paths on generic `main`. Copy and review configuration in an independent authority domain instead. The complete contract is at `docs/configuration.md` in a source checkout and `skill_delegator/docs/configuration.md` in an installed wheel.
