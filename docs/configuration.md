# Configuration Reference

One authority uses four shared YAML files (`authority.yaml`, `sources.yaml`, `pool.yaml`, and
`skill-lock.yaml`) plus exactly one delegation format:

- legacy: one aggregate `delegations.yaml`; or
- per-target: one or more singular `delegations/<target-id>.yaml` files.

`delegations.yaml` and `delegations/` are mutually exclusive. The loader fails closed if both or
neither exists. The legacy format remains supported; use the per-target format when target
declarations are deployed independently.

Owner-authored files use `schema_version: 1`. Generated locks use `schema_version: 2`. Strict JSON
Schema rules reject unknown fields and duplicate YAML keys.

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

## `delegations/<target-id>.yaml`

The singular per-target format uses one document for each target:

```yaml
# delegations/worker.yaml
schema_version: 1
target:
  id: worker
  root: /opt/agent/skills
  grants:
    - shared/code-review
```

Each file is validated against `target-delegation.schema.json`. That schema reuses the exact
target definition from `delegations.schema.json`, so target IDs, roots, and grants have the same
validation rules in both formats. The filename must be `<target.id>.yaml`; only regular `.yaml`
files are accepted. Files are discovered in filesystem-byte order, and duplicate target IDs fail
closed with the responsible filename.

Do not keep an empty `delegations/` directory and do not place `delegations.yaml` beside it.

## `skill-lock.yaml`

Run this command to generate the file:

```console
uv run skillctl lock --config my-config
```

A filesystem lock has this shape:

```yaml
schema_version: 2
hash_algorithm: sha256-portable-v2
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

`tree_hash` identifies the source-oriented locked snapshot. Each skill also has its own content
hash. Portable Hash V2 normalizes directory and symlink modes and retains only the regular-file
executable distinction. Source-local `.gitignore` files are the sole generated/dependency
exclusion policy: nested rules, negation, rooted patterns, and directory patterns are honored;
the `.gitignore` files themselves are hashed. Global excludes, `.git/info/exclude`, user Git
configuration, and ambient repository settings are never consulted. Ordinary nonignored
untracked files remain identity-bearing.

Legacy schema-v1 locks remain schema-valid only as a bounded migration input. Commands that
consume exact identities fail with a concise instruction to run `skillctl lock`; the regenerated
v2 lock explicitly separates portable identities from legacy hashes. Cached snapshots are likewise
namespaced as `<source-id>/<hash-algorithm>/<revision>`.

The tool checks source sets, types, paths, canonical IDs, runtime names, pool entries, grants, and hashes at each consumption boundary.

## Runtime Names and Target Paths

A skill gets its runtime name from the `name` field in `SKILL.md` frontmatter.

A runtime name can contain 1 to 128 ASCII letters, numbers, dots, underscores, or hyphens. It must start with a letter or number.

The target link uses the canonical artifact ID, not the runtime name:

```text
<target-root>/<source-id>/<path-relative-to-skill-root>
```

## Scoped and Unscoped Root Semantics

`plan`, `apply`, `verify`, and `status` accept `--target <exact-id>`. A scoped command resolves the
whole authority configuration but scans, fingerprints, or changes only the selected target. With
per-target declarations, equal or nested configured roots are allowed for a scoped command. This
is intended for separately deployed containers whose private mounts have the same in-container
path:

```yaml
# delegations/reviewer.yaml
schema_version: 1
target:
  id: reviewer
  root: /opt/agent/skills
  grants:
    - shared/code-review

# delegations/worker.yaml
schema_version: 1
target:
  id: worker
  root: /opt/agent/skills
  grants:
    - shared/testing
```

Deploy the complete configuration to both containers. Run `--target reviewer` only in container A
and `--target worker` only in container B. Equal path strings are safe here because each container
supplies a distinct filesystem namespace and each invocation touches one deployment scope.

Without `--target`, a per-target command is authority-wide. It requires every configured target
root to be disjoint. Equal roots and parent/child roots fail before any target scan or mutation;
distinct roots are processed normally. Legacy aggregate declarations retain their existing
whole-authority collision rules.

## Deterministic Configuration Provenance and Receipts

`verify` and `status` hash the complete configuration input set. The evidence contains relative
names and SHA-256 values for the four shared files and either the single `delegations.yaml` or
every singular `delegations/<target-id>.yaml`. A target-scoped operation still binds every config
file, while its target fingerprints and operation counts cover only the selected target.

The evidence also identifies every locked source, its hash algorithm, and the exact repository commit when it
is available (or explicitly records that it is unavailable). Configuration names and evidence
collections are deterministically ordered. A converged verification receipt is canonical JSON;
its filename is the SHA-256 of its bytes. Repeating verification against identical repository,
configuration, source, and selected-target evidence therefore returns the same receipt path and
byte-identical content.

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

After you edit the three shared owner-maintained files and one delegation form, generate the exact
lock:

```console
uv run skillctl lock --config my-config
uv run skillctl validate --config my-config
uv run skillctl resolve --json --config my-config
uv run skillctl plan --json --config my-config
```

Review every shared and delegation file and the complete plan. Commit the accepted configuration
before you apply it.

Then run:

```console
uv run skillctl apply --config my-config
uv run skillctl verify --config my-config
uv run skillctl status --json --config my-config
```

For independent target operators, pass the same exact target ID to each target-sensitive command:

```console
uv run skillctl plan --json --target niles --config my-config
uv run skillctl apply --target niles --config my-config
uv run skillctl verify --target niles --config my-config
uv run skillctl status --json --target niles --config my-config
```

The selector is available on `plan`, `apply`, `verify`, and `status`. An unknown ID fails before target scanning or mutation. Without `--target`, these commands retain their authority-wide behavior. `resolve` always reports the complete authority desired state.

`apply` recomputes and immediately executes a new plan. It does not consume the displayed `plan` output.

CAUTION: `--yes` authorizes each REMOVE in this new plan. Use it only when you accept this V1 limit.

## Migrating from Legacy to Per-Target Files

1. Save the accepted `skillctl resolve --json --config my-config` output for the legacy tree.
2. In a temporary review tree, create `delegations/<target-id>.yaml` for every entry in
   `delegations.yaml`. Change only the envelope from top-level `targets` to one top-level `target`
   per file; preserve each target object exactly, and make every filename stem equal its ID.
3. Remove `delegations.yaml`. Never run the CLI while both forms exist; mixed form is rejected.
4. Run `skillctl validate --config my-config` and `skillctl resolve --json --config my-config`.
   Compare the new resolved JSON with the saved legacy output. Target ordering and JSON output are
   deterministic, so an unchanged authority resolves identically.
5. Commit and deploy the complete conversion as one change. Do not deploy an empty or partial
   `delegations/` directory.
6. In each target's isolated environment, run `plan --target <target-id>`, review the plan, then
   run scoped `apply`, `verify`, and `status`. Use unscoped operation only when all target roots are
   disjoint in that environment.
