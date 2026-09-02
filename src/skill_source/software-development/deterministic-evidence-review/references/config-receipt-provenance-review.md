# Configuration receipt provenance review

Use this checklist when a verifier hashes configuration/lock inputs, optionally attaches a Git commit, and publishes a content-addressed receipt.

## Commit-to-bytes binding

A tracked pathname is not proof that Git tracks the bytes read through that pathname. A tracked symlink may point outside the repository while ordinary `Path.read_bytes()` follows it.

Probe with a temporary repository:

1. Create the required config inputs, making one a symlink to an external file.
2. Track and commit all config pathnames.
3. Run the production repository-commit discovery and receipt binding.
4. Compare the bytes hashed by the receipt with the Git object at `HEAD:<path>`.
5. The commit must be unavailable unless every hashed input is a regular, non-symlink file governed by the same repository and the implementation's stated binding contract is truthful.

Prefer opening each input without following symlinks, validating it as a regular file, hashing those exact opened bytes, and using the same validated path set for the Git-ownership decision. Do not perform a path-based Git check and a separate following read and call them one provenance boundary.

## Independent fresh scans

Target drift must not suppress source verification. Build a combined fixture after apply:

- remove or break one managed link; and
- tamper with that desired skill's exact cached source.

The result must preserve both independent observations (for example, missing-link drift and source-hash drift). Avoid `continue` paths after target scan failures that skip all desired source scans. Scan desired sources independently, then reconcile target observations.

## Model-to-evidence snapshot binding

An internally stable reread at receipt-binding time does **not** prove that the hashed configuration produced the already-verified model. Trace one immutable snapshot end to end:

1. At configuration loading, capture the deterministic lexical input-name set plus each exact byte payload, immediate-parent identity, file identity, regular-file type, and size through descriptor-relative no-follow reads.
2. Parse every model—including a separately consumed lock model—from those captured bytes. Do not validate one payload and later parse another pathname read.
3. Carry the frozen snapshot with the loaded authority through resolution and verification. A manually constructed authority may keep the field optional for source compatibility, but provenance binding must fail closed when no loader-originated snapshot exists.
4. Derive receipt hashes and Git blob comparisons from the carried snapshot bytes and identities, not from a fresh independent snapshot. Git availability requires the exact committed dynamic path set and every ordinary blob to match those bytes.
5. Compare a newly captured current state with the carried snapshot before status return and immediately before receipt publication. Reject changed input sets, parent/file identities, type, size, or bytes with one bounded diagnostic.

Regression timing matters: replace a valid same-name dynamic config file **after target verification and before evidence binding**. Parameterize both changed bytes and same bytes with a new inode, and run both `verify` and `status`. Require bounded failure, empty stdout, no published receipt or receipt staging residue, and no config-replacement temporary residue. The changed-byte case proves model/hash coherence; the same-byte case proves identity rebinding rather than hash-only comparison. Also probe legacy input sets, byte-sorted multi-file sets, `require_lock=False` (whose snapshot intentionally omits only the lock), and direct Git-evidence invalidation after same-byte inode replacement.

## Strict receipt semantics

Structural JSON Schema constraints are not enough for an evidence document. Probe at least:

- five entries with the same allowed config filename but different hashes;
- Git source paired with filesystem `tree_hash` / non-null tree identity;
- filesystem source paired with `resolved_commit` / null tree identity;
- duplicate source IDs or target fingerprint IDs;
- result, reason category, and summary-count contradictions.

`uniqueItems` on whole objects does not ensure unique names. Enforce the exact required filename set and source-type/revision-kind coherence in schema or in a strict semantic validator called by the public writer.

## Receipt-blocked CLI boundary

Fault-inject filesystem operations during every publication phase, including ancestor/root open, mkdir, ancestor fsync, file fsync, no-overwrite install, directory fsync, identity recheck, and cleanup. Every ordinary filesystem failure must normalize to the receipt-domain exception so the CLI returns its documented blocked exit code without traceback. A helper that closes resources and re-raises raw `OSError` can bypass a caller that catches only the domain exception.

## Implementation closure pattern

When remediating these findings, use one coherent evidence-honesty boundary rather than four unrelated patches:

1. **Read first, bind second.** Open each required config input through a bounded no-follow read, reject symlinked/non-regular lexical components, retain the exact bytes, and derive `config_hashes` from those bytes. Normalize the config root to an absolute lexical path before repository discovery.
2. **Prove the commit directly.** Resolve `HEAD^{commit}` without requiring a branch, inspect each exact path at that commit, require one ordinary blob entry (`100644` or `100755`), read that blob, and compare its bytes with the retained current bytes. Dirty files, tracked symlink entries, non-blobs, unrelated ancestor repositories, missing paths, and any Git error make the repository field explicitly unavailable. A clean detached commit remains available. Invoke Git with an argv list and no shell.
3. **Inspect desired sources before target reconciliation.** For every desired link, independently hash and inspect fresh source metadata first. Cache only that observation for target-link checks; do not rescan through target-dependent branches. Track source-clean state per artifact, mark both participants unverified when runtime names collide, and deduplicate reasons before deterministic sorting. A target-level failure must prevent verified-link credit without suppressing source findings.
4. **Validate document shape before cross-field semantics.** Use schema tuple/prefix positions for the canonical config filename order and source-type branches for Git versus filesystem identity. Then apply semantic checks that JSON Schema cannot naturally express: unique source IDs, filesystem `tree_identity == revision`, summary counts matching reasons, result/category coherence, no duplicate findings, and `verified_links <= desired_links`. Running schema validation first ensures malformed runtime values become the receipt-domain error instead of causing accidental `TypeError` in semantic code.
5. **Treat cleanup as part of the public error boundary.** Wrap root-anchor open, traversal open/mkdir/fsync/close, existing-file open/read/close, temporary publication, install, directory fsync, identity checks, unlink, and final descriptor closes. In `finally`, collect cleanup failures so every cleanup step still runs; then raise one bounded receipt-domain exception. The CLI must print verification/receipt output only after successful publication, so blocked publication returns the documented code with empty stdout and no traceback.

Regression fixtures should distinguish two symlink cases: a currently symlinked input must never be followed for hashing, while a commit containing a symlink entry with a current ordinary file must produce an explicit unavailable repository binding. Pair dirty-byte tests with a direct Git-blob hash inequality assertion so the test proves byte binding rather than merely Git status behavior. Also preserve a package-identity test for the strengthened schema and a hash check proving any pre-existing managed-state schema remained byte-identical.

## Final closure traps

A no-follow final-file open is still insufficient when ancestor validation and the eventual open are separate pathname operations. Add a deterministic ancestor-swap probe after an intermediate/config-directory check. The reader must traverse from the filesystem anchor with retained `O_DIRECTORY | O_NOFOLLOW` descriptors and open the final regular file relative to the retained parent; it may read the retained original inode or fail closed, but must never hash replacement/external bytes. Capture each file's **actual immediate parent** `(st_dev, st_ino)` plus the file's `(st_dev, st_ino, st_size)` while reading, and compare both identities plus exact bytes before and after the bounded read. Do not require nested inputs such as `delegations/<id>.yaml` to share the config-directory inode: their coherent parent is the retained `delegations/` descriptor. Re-discover the complete dynamic input-name set before and after Git provenance discovery, then revalidate every parent/file identity and byte payload; additions, deletions, renames, legacy/directory form swaps, and directory/file identity swaps must close the binding or make repository provenance unavailable.

For dynamic config sets, use the canonical discovery interface as the sole working-tree source and preserve its byte-sorted order through hashing and receipt semantics. Git evidence may independently enumerate the committed delegation subtree, but availability requires its exact relative blob-path set to equal the discovered current dynamic set and every committed ordinary blob's bytes to equal the retained bytes.

When a JSON Schema uses `pattern` for dynamic receipt names, include `"type": "string"` in that branch. JSON Schema string keywords are vacuously satisfied by non-string instances, so `{ "pattern": "..." }` alone can admit `null`, numbers, arrays, or objects through an `anyOf` or `contains`. Probe those JSON-native classes directly. Also exercise the runtime writer with malformed model values: schema and semantic validation must reject them through the receipt-domain exception, not leak `TypeError` from sorting, regex matching, or set membership. Keep ordering and identity uniqueness enforced semantically rather than relying on whole-object `uniqueItems`.

Receipt publication also needs one explicit success/error invariant. If the public writer reports failure after installing the content-addressed JSON, a newly published file must not remain. Duplicate the anchored publication directory descriptor before publication and postpone every success return until temporary cleanup and primary-descriptor close are finished. On a late failure, remove only a name created by this call through the retained cleanup descriptor and fsync it; never delete a pre-existing identical receipt. The cleanup descriptor itself is the final close. Choose and document one contract for that close: either ignore its post-commit close error and return success, or retain another rollback capability before reporting failure. Test both late-primary-close rollback and final-cleanup-close behavior directly. Do not return failure while leaving a new receipt behind.

When fault-injecting Python filesystem closes, remember that imported `os` references usually point to the same mutable module object: patching `receipts.os.close` can also intercept unrelated verifier closes. Target a module-local close seam when the test is component-specific, or discriminate exact descriptor identities/paths so the intended publication phase—not earlier config traversal—actually fires. Always assert the injection fired at the named checkpoint.

Cross-field coherence must make `converged` stronger than “no reasons.” Require `verified_links == desired_links`, zero drift/invalid counts, and coherent unique target-fingerprint evidence. Directly pass an impossible public `VerificationResult` (for example, two desired links, one verified, no reasons) to the writer and require rejection. Keep drift/invalid results able to report partial verification without inventing missing findings.

## Minimal evidence to report

Record exact source lines, the adversarial fixture property, actual output/exception type, focused and full test counts, schema artifact hashes, base-schema identity, and final repository status. Keep spec compliance and task quality verdicts separate. If the implementation report is ignored rather than tracked, append the evidence locally but do not silently force-add it unless the task explicitly requires the report in the commit.