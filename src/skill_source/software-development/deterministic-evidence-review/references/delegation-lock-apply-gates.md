# Delegation lock/apply gate probes

Use these focused probes when a declarative reconciler locks source trees, applies selected artifacts, and emits verification receipts.

## Whole-source identity

If a lock or receipt names a whole-source identity (filesystem tree hash, Git commit, archive digest), verifying only granted artifact subdirectories is insufficient. In a temporary fixture, lock and apply a source containing granted and ungranted content, then mutate bytes outside every granted skill but inside the cached snapshot. Both no-change apply and fresh verification must fail or report drift before a receipt repeats the original whole-source identity. Trace fast paths explicitly: `Already converged` must not bypass source-identity verification. Receipt serialization must use freshly verified identity evidence, not merely copy the lock claim.

## Lexical filesystem-source TOCTOU

A preflight loop of pathname-based `lstat()` calls is not sufficient when later discovery, hashing, or copying reopens the same lexical source path. The checked chain can be replaced after the final check, causing a symlink or different inode to become the effective source while the generated lock remains internally hash-consistent.

Build a deterministic temporary probe rather than relying on timing:

1. Create a configured lexical source with valid content and a separate outside tree with different, valid content.
2. Interpose the final source-component `lstat()` (or the narrowest equivalent boundary). Return the original metadata, but immediately rename the checked source and replace its lexical pathname with a symlink to the outside tree.
3. Run the real source resolver through cache publication.
4. Fail the gate if outside content is discovered or cached, even when the resulting tree hash and artifact hashes are self-consistent.
5. Assert the configured location remains the original lexical path so the evidence clearly demonstrates a path-to-inode binding failure.

The hardened design should retain no-follow directory descriptors and inode identities from anchor to source, then perform validation/hash/copy through that retained capability (for example descriptor-relative operations or a carefully verified `/proc/<pid>/fd/<n>` adapter). Revalidate every retained edge before publication. Static symlink/non-directory fixtures are necessary controls but do not cover this changed-line race.

## Hostile discovered identities

Validate identities at discovery, not only when configured as grants. Probe source directory components containing newlines/controls, leading dots, backslashes, non-canonical Unicode, excessive length, and characters outside the published canonical-ID grammar. UTF-8 encodability is not identity-policy validation. Require discovery, generated-lock schema, handwritten consumers, and pool/grant grammar to agree; an ungranted artifact must not smuggle a malformed canonical ID into a persisted lock.

When runtime names have their own grammar, compare the exact pattern bytes across discovery, published schema, and lock consumer. Pair hostile cases with established valid examples so hardening does not narrow the accepted contract accidentally.

## Hidden configured roots versus canonical identity

When a source can configure a snapshot-relative root such as `.claude/skills`, keep two path domains separate:

- the public lock `path` is the full snapshot-relative lexical path, so safe hidden segments may occur in the configured-root prefix;
- the canonical artifact ID suffix is relative to that root and must retain the stricter non-hidden canonical grammar.

Review this as a combined schema-and-semantic boundary. The lock-path schema should reject absolute paths, empty/repeated/trailing separators, exact `.` or `..` segments anywhere, backslashes, C0 controls/NUL, DEL, and surrogates. The loader must additionally reject filesystem-unencodable values before constructing a normalized path object. Do not rely on `PurePosixPath` or equivalent normalization to preserve evidence of repeated separators or `.` segments: test their original strings directly through the published schema/loader.

The resolver must bind `lock.path` to **exact lexical concatenation** of configured `skill_root` plus the canonical suffix. Probe a valid hidden-root control and reject at least: missing root, wrong root segment, root-prefix confusion (`skills-hidden` versus `skills`), wrong suffix, traversal/normalization confusion, an extra suffix, and an extra hidden suffix. Pair direct schema and resolver tests with a temporary public `lock -> validate -> resolve` sequence that proves `.claude/skills/banner-design` remains the source path while `source/banner-design` remains the identity.

Also compare the source-root schema and discovery validation against the accepted base. A hidden-root compatibility fix should not silently weaken configured `skill_root` confinement or canonical discovery. Confirm packaging includes the changed schema/docs byte-for-byte and finish with an exact diff path inventory proving no authority configuration, generated state, or real target mutation entered the generic-engine change.

For read-only acceptance runs, disable pytest cache and bytecode writes where practical and build into temporary output directories. Be careful with `compileall -b`: it writes sibling `.pyc` files outside `__pycache__`. Prefer a temporary `pycache_prefix`/destination, or remove only the generated files and recheck `git status --short` before claiming a clean review.

## Target-scoped operation isolation

When a CLI adds a selector such as `--target`, review isolation as an ordering property, not merely as a filtered loop:

1. Separate **whole-authority validation** from **target-root I/O**. Validate source/lock closure and all pure cross-target invariants before filtering, then scan or mutate only the selected target.
2. Trace every function called before selection. A configuration loader may claim not to read target contents yet still call `is_symlink()`, `exists()`, `is_dir()`, `stat()`, or `resolve()` for every configured target under a fixture/safety policy. Such preselection metadata reads violate a strict “do not read other targets” contract.
3. Probe root aliases. Configure two distinct target IDs whose lexical roots are identical and whose grants overlap. An unscoped resolver may reject the resulting path collision, while filtering the configuration before resolution can hide it and let scoped apply mutate a root also owned by the unselected target. Also test normalized aliases (`a/../root`), nested roots, and platform-equivalent spellings where supported.
4. Do not filter the authority model before pure cross-target semantic checks. Prefer resolving/validating the complete authority into an immutable desired state, selecting the requested target from that result, and only then performing current-state scans and mutations.
5. Verify selected receipts/status identify the selected target and the exact coverage count, while retaining whole-authority source/lock evidence where the receipt contract requires it. A single-target fingerprint is not a substitute for whole-source validation.
6. Exercise the selector error boundary with unknown, empty, very long, newline/control-bearing, and syntax-invalid values. Diagnostics must remain bounded, escaped, single-line, and emitted before any target-root scan or mutation.

For each scoped command (`resolve`, `plan`, `apply`, `verify`, and `status`), instrument target-root access or use hostile unselected roots so the test proves absence of reads rather than merely absence of writes. Pair scoped probes with unscoped controls to show legacy authority-wide behavior is unchanged.

## Bounded numeric controls

For lock timeouts, retry budgets, and scheduler limits, require `math.isfinite()` before arithmetic or loops. A guard such as `value < 0` accepts `NaN`; deadline comparisons then never become true and can turn a timeout into an infinite wait. Probe negative, zero, finite positive, `NaN`, `+inf`, and `-inf` through the real CLI under actual contention, using an external process timeout as the oracle.

## Installed-wheel release boundary

Source-tree tests do not prove packaged resources or entry points. For a release gate, build wheel and sdist into a temporary output directory, install the wheel offline into a fresh interpreter environment, and run from a temporary project outside the source tree with `PYTHONPATH` removed.

Verify all of the following from the installed wheel:

- every documented command appears and executes through the installed console entry point;
- the packaged example and fixture can be copied with `importlib.resources` and run through `validate -> lock -> resolve -> plan -> apply -> verify -> status` twice;
- first plan/apply creates the exact links, second plan/apply converges (allow informational preservation operations when asserting KEEP actions); treat the plan command's documented “changes present” exit (commonly `1`) as expected evidence rather than using unconditional `check=True`;
- raw symlink destinations, manager metadata fields, cache identity, receipt filename-as-byte-hash, and repeated receipt path/bytes are exact;
- `status` leaves config, source fixture, target state, receipts, and tracked status byte-identical;
- config/source bytes and Git tracked status remain unchanged across both runs;
- wheel and sdist contain exact source bytes for the required schemas, docs, example YAML/README, and fixture;
- archives exclude task/review artifacts, local cache/target/receipt state, credentials, and source-control residue.

Do not confuse a whole-source tree hash with an individual skill-content hash when checking metadata. Derive each expected identity from the lock or normative fixture rather than assuming the two hashes coincide. Likewise, a converged plan may include informational `PRESERVE_UNMANAGED` operations around manager metadata; filter only those documented informational actions before asserting the exact KEEP set.

## Receipt fail-closed matrix

A verifier detecting whole-snapshot drift is not sufficient if the CLI still serializes or publishes a receipt afterward. Exercise filesystem and Git sources separately because receipt semantics often differ:

- mutate ungranted cached content, run the real `verify` command, and require the established drift/invalid exit and deterministic status text **with no receipt line, no receipt directory, and zero newly published receipts**;
- run `status` against the same drift, require identical status/exit, and compare a complete before/after snapshot of mutable state to prove it is strictly read-only;
- restore the exact cached bytes, rerun `verify`, and require convergence plus exactly one deterministic receipt;
- for Git, compare the freshly observed full-tree hash directly with the lock's `tree_hash` before constructing receipt identity; a 64-hex shape check alone can publish a drift receipt pairing the locked commit with tampered bytes;
- keep Git `revision` equal to the exact locked commit and assign `tree_identity` from the lock's `tree_hash`, never from a mismatching observation; do not invent a commit-shaped tree identity;
- make the public writer reject every non-converged result before opening/creating the receipt root, and require exactly one fresh source-tree evidence item per locked source with evidence hash equal to the locked receipt tree identity;
- make converged evidence binding independently reject any missing, duplicate, extra, or mismatching whole-tree observation before receipt publication.

A filesystem-only tamper test can create false confidence when filesystem receipt semantics require `revision == tree_identity` but the Git branch checks only field shape. Pair direct writer-unit tests (drift, invalid, missing/mismatching evidence) with the real offline Git CLI sequence above.

## Canonical grammar and schema-engine traps

Test the published JSON Schema directly, independently of handwritten semantic consumers. In Python/jsonschema, an anchored pattern ending in `$` can match immediately before a final newline because schema `pattern` uses search semantics. Therefore include both embedded-newline and **trailing-control** fixtures for canonical IDs and locked paths: LF, CR, NUL, another `U+0000`–`U+001F` control, and DEL (`U+007F`). A later resolver rejection does not prove the schema enforces the same grammar.

JSON Schema's portable ECMAScript-oriented regex subset does not provide a universally safe Python-style absolute-end anchor. Preserve the established allow-list pattern, and augment it with an explicit negative control-class constraint such as `"not": {"pattern": "[\\u0000-\\u001F\\u007F]"}`. Apply the same closure to pool/grant canonical-ID schemas, then run direct Draft 2020-12 validation for each schema as well as config-loader/discovery/resolver controls. Pair every hostile case with established valid IDs so hardening does not narrow the accepted contract.

For ancestor-swap race fixtures, make the replacement ancestor point to a directory containing the same remaining suffix as the configured path. Example: if the configured path is `parent/source`, replace `parent` with a link to `outside-parent` where `outside-parent/source` contains hostile bytes. Linking to `outside.parent` without constructing `<outside.parent>/source` does not actually test redirection. Assert the swap fired, the replacement lexical path resolves to the hostile tree, hostile runtime/content differs from the original, resolution rejects the identity change, and neither hostile bytes nor any cache entry are published.

## Changed-line documentation truth

When identity fields or cache keys change, compare changed documentation literally against the storage call. Distinguish Git commit-keyed cache paths, tree-hash-keyed filesystem paths, whole-tree evidence, and individual artifact hashes. A passing installed-wheel smoke does not validate prose that names the wrong cache key.

## Authority-only review after an accepted generic merge

When an authority branch merges an already accepted generic-engine commit and then adds authority configuration, review the two layers separately rather than treating the three-dot range as one undifferentiated patch:

1. Pin the old authority tip, accepted generic commit, merge commit, and final HEAD. Prove the accepted generic commit is an ancestor of HEAD.
2. Compare accepted generic commit to final HEAD over generic engine, tests, CI, packaging, and generic documentation paths. Require byte identity unless an explicitly approved conflict resolution says otherwise. For a formerly unsafe file, also compare its blob hash and inspect the final security seam directly; merge ancestry alone does not prove the unsafe side was discarded.
3. Compare merge commit to final HEAD for the authority-only path inventory. This prevents inherited generic documentation changes from being misreported as new authority scope and exposes unauthorized config, source, or target additions.
4. For canonical-ID corrections, compare old and new pool/grant sets after applying an explicit one-to-one rename map. Require equal cardinality and normalized set equality per pool and per target; raw textual diffs can disguise either accidental expansion or accidental removal.
5. Validate lock closure independently: for every source, recompute the whole-tree hash, rediscover every skill, and compare the exact canonical ID, runtime name, source path, and artifact hash. Then require unique lock IDs, pool subset of lock, and every target grant subset of pool.
6. For pinned external commits, verify the commit exists at the named upstream and compare the upstream recursive `SKILL.md` directory set with the locked canonical-ID set. Preserve the source-owner prefix in nested IDs so path correction does not erase attribution.
7. For vendored files with provenance, fetch the named upstream commit and byte-compare every file claimed to be unchanged, including the license. Cite the local provenance, retained attribution, and license lines separately.
8. Reconcile reported sandbox action counts from configuration without touching targets: sum grants only after proving per-target runtime names are collision-free. This makes a reported all-CREATE first run and no-op second apply plausible without reproducing a prohibited apply.
9. Treat intentional stale-document deletion and documentation closure separately. Deleting a safe-example README can be correct when the branch is no longer the safe fixture, while surviving links to that deleted file remain a non-blocking documentation defect unless they affect an operator safety contract.
10. Finish by proving the worktree identity and clean status. Do not inspect real target roots or run apply when the review brief forbids them.

## Evidence

Pair each hostile fixture with a valid control. Record exact source lines, actual exit/output, before/after mutation state, and targeted/full gate results. Keep probes and build outputs in temporary directories and finish with exact commit/status/diff checks. Do not accept passing happy-path tests as proof of these boundaries.
