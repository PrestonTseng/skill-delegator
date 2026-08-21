# Architecture

## One Authority per Invocation

`skillctl` reads one configuration directory during each invocation.

The engine has no parent registry or cross-authority traversal. Pool rules, grants, locks, names, and target paths apply to one authority only.

Independent authorities can use the same code and keep separate configuration histories. This version-control pattern does not create an authority hierarchy.

## Data Flow

```text
sources.yaml ──lock──> immutable cache + skill-lock.yaml
five configuration files ──resolve──> desired state
desired state + target scan ──plan──> reconciliation plan
current configuration + fresh target scan ──apply──> new plan + managed state
fresh source and target evidence ──verify──> verification receipt
```

`validate`, `resolve`, `plan`, and `status` do not change targets.

`lock` changes only the exact lock and ignored source cache. `update` changes only source observations or the candidate lock.

`apply` is the only command that changes targets. `verify` can write a receipt but does not change sources or targets.

`apply` recomputes and immediately executes a new plan. It does not consume or bind to displayed `plan` output.

## Skill Identity

A canonical skill ID has this form:

```text
<source-id>/<path-relative-to-skill-root>
```

A configured `skill_root` can contain safe hidden segments. Those segments do not become part of the canonical skill ID.

The lock records the complete source path. Resolution requires an exact match between this path, the skill root, and the canonical suffix.

A skill gets its runtime name from `SKILL.md` frontmatter. Duplicate runtime names in one target fail closed.

The canonical artifact ID sets the link path:

```text
<target-root>/<artifact-id>
```

## Exact Source Locks

`apply` uses only exact lock identities and skill hashes.

A Git lock records the resolved commit and a SHA-256 hash of the source-oriented snapshot.

A filesystem lock records the same snapshot hash as its revision. Portable Hash V2 uses fixed
semantic modes for directories and symlinks and records only executable versus non-executable for
regular files. Paths, entry kinds, file bytes, and symlink target bytes remain identity-bearing.

Only source-local `.gitignore` files exclude generated or dependency content. Nested rules,
negation, rooted patterns, and directory patterns use Git-compatible semantics; `.gitignore`
files themselves remain identity-bearing. The engine never reads global excludes,
`.git/info/exclude`, or ambient Git configuration. Nonignored untracked files remain part of the
snapshot identity.

Mutable Git `track` values are update inputs. `apply` never uses them as exact identities.

Source snapshots use content-addressed cache paths below
`var/cache/sources/<source-id>/<hash-algorithm>/<revision>/`, so legacy and portable identities
cannot collide on disk.

## Target Model

V1 publishes each delegated skill as a symlink. It also writes manager records, transaction data, cache snapshots, and receipts.

It records managed links in `<target>/.skill-delegator/managed.json`.

Other files, directories, and links are unmanaged. The tool preserves them.

A REMOVE operation needs a valid manager record. The CLI also requires `--yes`.

## Apply Transaction

The reconciler locks targets in a stable order. It uses target inode locks and `.skill-delegator/operation.lock`.

It scans the state again after it gets the locks. Then it stages links and checks exact source content.

The reconciler keeps backups while it publishes links and manager records.

Before all manager records are published, an error starts a bounded rollback. The rollback uses retained descriptors, backups, and link journals.

After all manager records are published, the transaction is committed. A later cleanup error does not report a rollback.

A multi-target apply gives process-level transaction behavior. It is not one atomic filesystem operation.

## Lock Publication

Lock publication uses one atomic `os.replace` after all staging and identity checks pass.

This replacement is the lock commit boundary. The tool does not restore an old lock after this point.

Use reviewed Git history to restore an older lock. Then run `plan`, `apply`, and `verify` again.

## Verification Receipts

Verification hashes each complete filtered cached source snapshot once. Ungranted, nonignored
source changes also invalidate the evidence.

A receipt uses canonical JSON with a final newline. Its filename is the SHA-256 hash of those exact bytes.

Receipt publication does not overwrite an existing file. Identical evidence uses the same receipt path.

## Packaging

The wheel contains the schemas, documents, and safe example.

The source distribution also contains the tests and fixtures that reproduce the release checks.
