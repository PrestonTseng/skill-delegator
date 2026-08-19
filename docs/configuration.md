# Configuration Reference

One authority uses one directory with five YAML files.

All files use `schema_version: 1`. Strict JSON Schema rules reject unknown fields and duplicate YAML keys.

Paths are relative to the configuration directory unless a field permits an absolute path.

## `authority.yaml`

```yaml
schema_version: 1
authority:
  id: team-a
  fail_closed: true
  fixture_policy: none
```

`id` uses lowercase letters, numbers, and hyphens. It must start with a letter.

`fail_closed` must be `true`.

Use `fixture_policy: none` for a real authority. `safe-main-example` is reserved for the checked-in example.

## `sources.yaml`

### Git source

```yaml
schema_version: 1
sources:
  - id: shared
    type: git
    location: https://github.com/example/skills.git
    track: main
    skill_root: skills
```

A Git source requires `track`. This value finds updates, but `apply` never uses it as an exact identity.

### Filesystem source

```yaml
schema_version: 1
sources:
  - id: local
    type: filesystem
    location: /srv/reviewed-skills
    skill_root: skills
```

A filesystem source must not contain `track`.

`skill_root` is a confined POSIX path inside the source snapshot. It can contain safe hidden segments, such as `.claude/skills`.

The tool rejects broken links, escaping links, and unsupported special files in a source tree.

The authority owner must review source trust. The tool records content identity but does not judge instruction safety.

## `pool.yaml`

```yaml
schema_version: 1
skills:
  - shared/code-review
  - shared/testing
```

A canonical skill ID has this form:

```text
<source-id>/<path-relative-to-skill-root>
```

The list must contain at least one unique skill ID.

Nested directories below `skill_root` are preserved in both the canonical ID and the target link. For example, given this source:

```yaml
- id: vendor
  type: git
  location: https://example.invalid/vendor/skills.git
  track: main
  skill_root: skills
```

an upstream manifest at `skills/engineering/review/SKILL.md` has:

```text
canonical ID: vendor/engineering/review
target link:  <target-root>/vendor/engineering/review
runtime name: the name in SKILL.md frontmatter
```

Keeping the source ID and nested category in the link makes third-party provenance visible without changing the runtime name.

The pool is the maximum set that this authority can grant. Locking a source does not add discovered skills to the pool.

## `delegations.yaml`

```yaml
schema_version: 1
targets:
  - id: worker
    root: ../var/worker-skills
    grants:
      - shared/code-review
```

Target IDs must be unique. Each target needs at least one unique grant.

Every grant must exist in the pool and in `skill-lock.yaml`.

Two target entries cannot use the same normalized artifact path. Duplicate runtime names in one target also fail closed.

The current user needs write access to the target and each missing parent directory.

For production, use a dedicated target root and the least required privilege.

## `skill-lock.yaml`

Run this command to generate the file:

```console
uv run skillctl lock --config my-config
```

A filesystem lock has this shape:

```yaml
schema_version: 1
sources:
- source_id: shared
  type: filesystem
  tree_hash: <64 lowercase hex characters>
  skills:
  - canonical_id: shared/code-review
    runtime_name: code-review
    path: skills/code-review
    sha256: <64 lowercase hex characters>
```

A Git lock also records `resolved_commit`. It contains the exact 40-character Git commit ID.

`tree_hash` identifies the complete locked source snapshot. Each skill also has its own content hash.

The tool checks source sets, types, paths, canonical IDs, runtime names, pool entries, grants, and hashes at each consumption boundary.

## Runtime Names and Target Paths

A skill gets its runtime name from the `name` field in `SKILL.md` frontmatter.

A runtime name can contain 1 to 128 ASCII letters, numbers, dots, underscores, or hyphens. It must start with a letter or number.

The target link uses the canonical artifact ID, not the runtime name:

```text
<target-root>/<source-id>/<path-relative-to-skill-root>
```

## Generated State

The tool can create these paths:

- `var/cache/sources/...`: immutable source snapshots
- `<target>/.skill-delegator/managed.json`: exact manager ownership records
- `<target>/.skill-delegator/operation.lock`: an apply lock
- `<target>/.skill-delegator/staging/`: transaction staging
- `<target>/.skill-delegator/backup/`: retained transaction backups
- `<target>/.skill-delegator/failure.json`: bounded failure evidence
- `var/receipts/<sha256>.json`: verification receipts

Do not commit generated caches, example targets, transaction data, or receipts as configuration.

## First Configuration Workflow

After you edit the four owner-maintained files, generate the exact lock:

```console
uv run skillctl lock --config my-config
uv run skillctl validate --config my-config
uv run skillctl resolve --json --config my-config
uv run skillctl plan --json --config my-config
```

Review all five files and the complete plan. Commit the accepted configuration before you apply it.

Then run:

```console
uv run skillctl apply --config my-config
uv run skillctl verify --config my-config
uv run skillctl status --json --config my-config
```

`apply` recomputes and immediately executes a new plan. It does not consume the displayed `plan` output.

CAUTION: `--yes` authorizes each REMOVE in this new plan. Use it only when you accept this V1 limit.
