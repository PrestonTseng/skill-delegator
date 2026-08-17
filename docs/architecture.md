# Architecture

## One authority per invocation

`skillctl` loads one configuration directory and constructs one `AuthorityConfig`. The engine has no parent/child registry and no cross-authority traversal. Pool containment, target grants, lock completeness, runtime-name uniqueness, and target-path collision checks are scoped to that one object.

Independent authority domains can use the same code while retaining separate `config/` histories. A branch convention (`main` generic engine, separate authority branches) is a version-control workflow, not an authority hierarchy enforced by the process.

## Data flow

```text
sources.yaml ──lock──> immutable cache + skill-lock.yaml
     five config files ──resolve──> DesiredState
DesiredState + fresh target scan ──plan──> ReconciliationPlan
reviewed/rebuilt plan ──apply──> managed symlinks + managed.json
fresh desired/source/target evidence ──verify──> content-addressed receipt
```

`validate`, `resolve`, `plan`, and `status` do not intentionally mutate targets. `lock` mutates only the configured lock and ignored source cache. `update` is source/lock work only. `apply` is the sole target-reconciliation command. `verify` is read-only for sources/targets/config but may publish a receipt.

## Identity and placement

Artifact identity is `<source-id>/<relative-path-from-skill-root>`. The canonical suffix uses strict non-hidden segments even when the configured `skill_root` itself contains safe hidden segments. The lock separately records the full snapshot-relative source path as exact `skill_root + canonical suffix`; resolution requires that lexical equality rather than prefix-only containment. Runtime identity is a safe bounded `SKILL.md` frontmatter `name`; duplicate runtime identities per target fail. Artifact paths—not runtime names or configured source-root prefixes—determine symlink placement: `<target-root>/<artifact-id>`.

Apply consumes only exact lock identities and exact skill hashes. A Git lock binds both the resolved commit and a SHA-256 tree hash computed directly over the complete locked snapshot; a filesystem lock uses that complete tree hash as its revision. Mutable Git `track` values are update inputs, never apply inputs. Filesystem snapshots are cached at `var/cache/sources/<source-id>/<snapshot-tree-hash>/`; Git snapshots are cached at `var/cache/sources/<source-id>/<resolved-commit>/`. Both lock forms carry the complete snapshot tree hash.

## Symlink-only target model

V1 creates symlinks and records only its own entries in `<target>/.skill-delegator/managed.json`. Unrecorded files, directories, and links are unmanaged and preserved. A REMOVE operation is authorized only by a prior valid manager record and requires `--yes` at the CLI.

## Transaction and commit boundaries

For a mutating apply, targets are locked in stable order using both target-root inode locks and `.skill-delegator/operation.lock`. The reconciler re-scans under lock, stages links, verifies exact source content, promotes with retained backups, removes staging, and publishes canonical `managed.json` for every target. Until all metadata publications complete, failure triggers rollback from retained descriptor-anchored backups and exact inode/raw-link journals. Once all metadata has been published, the transaction is committed; later cleanup failure is reported as committed and is never presented as a rollback.

An apply transaction spans the configured targets in the invocation. This is process-level transactional behavior under the documented cooperative/local threat assumptions, not a filesystem-wide atomic primitive.

Lock publication has a separate boundary: all staging, fsync, identity, byte, parent, and prior-public checks happen before one atomic `os.replace`. Successful replace is the commit boundary. After it, the public lock pathname is observed only; it is never rolled back or overwritten by cleanup.

Verification freshly hashes every complete cached source snapshot once per source before claiming its locked identity, including ungranted content. Receipts record Git commit plus directly locked snapshot tree hash (or the filesystem tree hash), use canonical JSON plus newline, and are named by the SHA-256 of those exact bytes. Publication is no-overwrite/content-addressed; repeated identical evidence reuses the path.

## Packaging

JSON Schemas are package data and are read with `importlib.resources` when the source-tree schema directory is absent. The source distribution also carries README, configuration, docs, tests, and fixtures needed to reproduce the release gates.
