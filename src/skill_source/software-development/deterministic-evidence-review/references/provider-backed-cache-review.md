# Provider-Backed Historical Cache Review

Use this reference for immutable-history loaders that fetch an external provider once, validate strictly, and publish a reusable local cache.

## Provider realism

Synthetic fixtures must model the provider rather than an idealized protocol.

1. Read the maintained provider schema for required and documented optional fields.
2. Run a minimal read-only live probe over a tiny range. Record only structural facts needed by the review: keys, timestamp precision/offsets, ordering, page termination, and boundary inclusion.
3. Feed a representative live-shaped payload through the production adapter. A successful raw HTTP probe does not prove the adapter accepts it.
4. Preserve truthful source timestamps. If events nominally belong to fixed slots but arrive a few milliseconds after the boundary, validate exactly one strictly increasing event per slot; do not rewrite timestamps to make fixtures pass.
5. Add test-only fixtures for documented extra fields, timestamp jitter, duplicate/missing slots, exact-limit pagination plus empty terminator, out-of-range rows, and unchanged reader failures.

Strictness means rejecting ambiguous or invalid evidence, not rejecting valid provider evidence because a fixture omitted documented fields.

## Stable request versus source identity

Keep two identities separate:

- **Request namespace:** provider, venue/instrument, ordered frames, policy bytes/digest, fixed bounds, metric, and interval semantics. Exclude invocation time.
- **Source identity:** exact request plus original retrieval provenance and every canonical observation.

A later invocation may reuse a fully validated source only when `source.retrieved_at <= invocation_now`, with zero reader calls. Matching corruption or eligible ambiguity fails closed. Unrelated namespaces and non-source control files must not block a valid hit.

## Atomic no-overwrite publication

Judge the primitive by observable guarantees, not whether the code literally calls `rename`.

A same-directory hard-link install can satisfy atomic publication when:

- the temp is a regular private file in the destination directory;
- all bytes are written and the file is fsynced first;
- link insertion is atomic and fails with EEXIST rather than overwriting;
- temp unlink cannot remove/truncate the destination because both names share the inode;
- the containing directory is fsynced;
- destination is reopened no-follow, byte-compared, hash/schema validated;
- failure cleanup removes only the installed `(st_dev, st_ino)` and fsyncs again.

This can be stronger than `os.replace` when never-overwrite is binding. Do not flag hard-link publication merely because the prose says “rename.” Flag a concrete filesystem/portability incompatibility only when the supported environment exhibits one.

## Crash-durability chain

Audit metadata, not just data bytes:

1. fsync the completed temp file;
2. atomically install without overwrite;
3. unlink the temp name;
4. fsync the containing directory;
5. if root/request directories were newly created, fsync each parent that acquired a new directory entry;
6. on EEXIST, fsync after temp unlink if successful return promises no residue;
7. on every post-install failure, ownership-check, unlink only this attempt, and fsync while preserving the original error.

A directory fsync cannot make that directory's own link in its parent durable.

## Descriptor confinement

Static `lstat` followed by later path-based `scandir/open/mkstemp/link/unlink` leaves a directory-component TOCTOU window. `O_NOFOLLOW` on the final file does not protect intermediate components.

For an explicit no-symlink/private-cache contract:

- open root and namespace with `O_DIRECTORY|O_NOFOLLOW`;
- verify descriptors with `fstat`;
- retain them through scan, open, temp creation, link, unlink, cleanup, and fsync;
- use `dir_fd` plus entry names where available;
- test a concurrent namespace rename/symlink substitution, not only static symlinks.

### Descriptor ownership on exceptional verification paths

Treat `open → verify → return fd` as an ownership-transfer protocol. Once `open` succeeds, the helper owns the descriptor until it returns successfully. Every post-open failure must close it, including failures from the first `fstat`, mode repair (`fchmod`/`fsync`), the final `fstat`, and direct `BaseException` subclasses.

Use one outer `try/except BaseException` around all post-open verification. Avoid branch-local closes that can double-close when the outer guard also runs. If `close` itself fails, preserve the original verification exception and traceback; add the close failure as a diagnostic note rather than masking the primary error. A parent context manager must likewise release already-owned parent/root descriptors when opening or verifying a child directory fails.

Review with fault injection, not only happy-path fd counts:

- inject failures at first `fstat`, `fchmod`, repair `fsync`, and second `fstat`;
- assert the exact newly opened descriptor is closed and `/proc/self/fd` is unchanged where available;
- inject a close failure and assert original exception identity plus diagnostic context;
- fail child-directory verification after parent/root ownership and assert all owned descriptors close;
- verify a successful return leaves the descriptor open for the caller and that no validation branch double-closes a reused fd.

## Descriptor-native composition across layers

When a hardened caller already retains a cache-root directory descriptor, do **not** convert it to `/proc/self/fd/<n>` and pass that value into a loader whose Path API rejects symlinks with `O_NOFOLLOW`. Procfs descriptor entries are symlinks by design; treating one as a normal path creates an integration contract that can pass injected-loader tests yet fail before cache lookup or provider access.

Prefer a descriptor-native boundary:

- keep the existing Path API for ordinary callers;
- add an fd/handle route that duplicates the borrowed root descriptor internally, so the callee never closes the caller-owned fd;
- pass a separate trusted display path only for diagnostics and manifest labels, never for traversal;
- create/open request namespaces relative to the duplicated root fd with the same private-mode, no-follow, fsync, cache-hit, and atomic-publication semantics as the Path route;
- verify caller fd identity before and after evaluation when identity drift is a governed concern;
- do not fix the mismatch by resolving `/proc/self/fd`, weakening symlink rejection, or branching on function identity.

Regression coverage must exercise the **real default adapter**, not only an injected lambda. Include:

1. the exact caller→production-loader route with a retained cache fd;
2. cache hit with zero provider calls;
3. cache miss and durable publication via the fd route;
4. proof that the borrowed caller fd remains open;
5. no-follow/private-mode and identity-drift failures;
6. actual `python -m` invocation from a clean shell, because pytest `pythonpath` and dependency injection can hide a broken production seam.

A useful minimal diagnosis compares the same directory through both routes: ordinary Path should succeed, while `/proc/self/fd/<n>` passed to a Path-only no-follow loader reproduces the incompatibility. Capture that RED before changing the contract.

## TDD and review evidence

For a clean redo, prove:

- the complete test contract and fixture refinements predate production;
- fixture-only commits contain no production changes;
- production commit adds no tests;
- every prior finding has an explicit disposition;
- focused probes are used for concrete doubts instead of substituting a broad green suite;
- final report separates spec compliance, code quality, hard-link adjudication, new findings, and approval verdict.
