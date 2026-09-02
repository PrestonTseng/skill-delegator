# Byte-identical final evidence-package certification

Use this recipe when a versioned evidence package was produced twice with the same explicit time, commit, clean-status bytes, policy/config bytes, and retained cache, and the user wants a final certify-or-block decision without another expensive provider replay.

## Certification sequence

1. Pin `HEAD`, tree, raw porcelain-v1 `-z` status bytes, primary path, recheck path, and recorded process exits.
2. Require both exits to be zero and both directories to contain the exact allowlisted regular, non-symlink inventory. Explicitly reject raw bars, cache envelopes, replay pickles, and unexpected entries.
3. Compare every allowlisted file byte-for-byte. Hash primary and recheck independently; do not rely only on manifest-declared digests.
4. Reparse each JSON artifact with duplicate-key rejection when available. Require canonical sorted compact JSON plus one LF. Re-render Markdown only from the detached JSON mapping and require exact bytes.
5. Validate schema-native types recursively, not merely values: integers must be `type(x) is int` so booleans cannot satisfy count/version fields; booleans must be booleans; lists and objects need exact surfaces; SHA fields must be lowercase 64-hex strings.
6. Recompute dirty-state, committed source, config, artifact, request, cache-envelope, unsigned source-envelope, and normalized-series commitments from the exact bytes they claim to bind. Match intervals, retrieval/publication ordering, endpoints, provider/venue/symbol, and quality observed/expected counts.
7. If a prior independent full-tree recomputation proved zero mismatches for a result SHA, and the final result bytes have exactly that SHA, carry the proof forward by byte identity. State this explicitly. Do not rerun an expensive provider replay merely to re-prove unchanged result bytes.
8. Re-evaluate all screening gates independently from detached results, preserving frozen gate/reason order. Keep Evidence Integrity and Recommendation Quality as separate verdicts.
9. Run fresh focused/full tests, compile/static checks, final byte comparison, and final status/HEAD checks before writing approval.
10. Report the exact package decision, P0/P1/P2 counts, mismatch count, hashes, superseded-version disposition, residual limitations, and prohibited side effects.

## Exact-Decimal pitfall in ad-hoc certifiers

A verifier can falsely report failed cash reconciliation if it uses ambient Python `Decimal` precision while summing long coefficient strings. This commonly appears as a truncated 28-digit sum even when the published exact values reconcile.

For independent checks, use one of:

- a dynamically widened `localcontext()` whose precision exceeds the largest possible coefficient growth;
- exact integer-coefficient/Fraction arithmetic; or
- the project's reviewed exact summation primitive, only when independence is not required.

Start sums with `Decimal(0)` inside the widened context. Treat an initial ambient-context mismatch as a verifier defect until exact arithmetic confirms it. Never downgrade a package based on a rounded ad-hoc sum.

## Superseded immutable versions

If schema v1 was provenance-incomplete and schema v2 closes it, preserve v1 and label it blocked/superseded. Approval of v2 does not retroactively approve v1. Record whether the final package is ignored/untracked so the controller deliberately preserves the reviewed bytes.

## Approval boundary

A package can be approved as accurate evidence while its trading candidate is rejected. Phrase the two decisions separately:

- **Package:** approved or blocked as evidence.
- **Candidate:** survives or is rejected by the frozen screen.

Historical screening never authorizes promotion, deployment, scheduling, active-state mutation, or forward confirmation.
