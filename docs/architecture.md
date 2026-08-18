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
reviewed current plan ──apply──> managed symlinks + managed.json
fresh source and target evidence ──verify──> verification receipt
```

`validate`, `resolve`, `plan`, and `status` do not change targets.

`lock` changes only the exact lock and ignored source cache. `update` changes only source observations or the candidate lock.

`apply` is the only command that changes targets. `verify` can write a receipt but does not change sources or targets.

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

A Git lock records the resolved commit and a SHA-256 hash of the complete source snapshot.

A filesystem lock records the same complete snapshot hash as its revision.

Mutable Git `track` values are update inputs. `apply` never uses them as exact identities.

Source snapshots use content-addressed cache paths below `var/cache/sources/`.

## Target Model

V1 creates symlinks only. It records its entries in `<target>/.skill-delegator/managed.json`.

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

Verification hashes each complete cached source snapshot once. Ungranted source changes also invalidate the evidence.

A receipt uses canonical JSON with a final newline. Its filename is the SHA-256 hash of those exact bytes.

Receipt publication does not overwrite an existing file. Identical evidence uses the same receipt path.

## Packaging

The wheel contains the schemas, documents, and safe example.

The source distribution also contains the tests and fixtures that reproduce the release checks.
