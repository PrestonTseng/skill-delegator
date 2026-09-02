# Immutable Screening Publication Provenance

Use this checklist before launching an expensive deterministic replay or calling a package final. Arithmetic correctness is necessary but does not make detached evidence self-authenticating.

## Design-to-manifest closure

Build a field-by-field matrix from the approved design to the manifest schema. At minimum bind:

- code commit and a **pre-run dirty-state fingerprint**: exact Git command/scope, SHA-256 of its raw bytes, entry count, and the clean scope relied on by execution;
- scored, warm-up, and fixed segment boundaries;
- provider, venue, symbol, fixed endpoint identities, canonical request bytes/hash, and retrieval time;
- source-series content hashes plus the exact validated cache/envelope byte count and SHA-256; where the envelope has an unsigned content hash, retain that too;
- explicit data-quality results and observed/expected counts for each bar frame and funding series;
- policy/config hashes, artifact hashes, cost model, and publication time.

Do not infer that source-series hashes are equivalent to a cache-envelope commitment. Detached consumers need both normalized-series identity and the container/request provenance that produced it.

## Byte-bound provenance

Provenance must come from the exact bytes that were decoded and validated:

1. Open through the retained trusted directory descriptor with no-follow semantics.
2. Read once from that descriptor.
3. Hash those bytes and decode/validate those same bytes.
4. Carry hashes/counts in an immutable provenance object returned with the validated bundle.
5. Build the manifest from that object—never by reopening the pathname later.

Apply the same rule to cache-hit and freshly fetched paths. For fetches, hash the canonical envelope bytes that are actually published and reread; do not construct an equivalent-looking hash from selected fields.

## Quality claims

A manifest may say `PASS` only for checks the loader really performed. Keep an explicit mapping between validator functions and durable claims, covering:

- provider/venue/symbol/timeframe identity;
- UTC and cutoff causality;
- closed bars and finite valid OHLC;
- strict chronology, continuity, and full expected coverage;
- funding provider identity, slot coverage, units, and normalized/source agreement;
- source-hash verification.

Record observed and expected counts per series. Tests must reject missing checks, unknown checks, failed statuses, count drift, endpoint drift, request/envelope hash drift, and bool-as-int substitutions.

## Determinism and immutable remediation

Generate the manifest twice with identical commit, cache bytes, explicit `NOW`, and Git-status bytes; require byte identity. Primary and recheck runs should use the same explicit `NOW`.

If an immutable package is later found provenance-incomplete:

- do not overwrite, rename, or delete it;
- mark it blocked/superseded in the review record;
- fix and review the schema first;
- publish a new versioned directory;
- avoid spending hours rerunning a known-obsolete schema;
- rerun the final schema twice and compare policy, result, report, and manifest bytes.

A nonpublishing harness built from a validated replay may accelerate schema/report debugging, but it is supporting evidence only. The final package must still be produced by the reviewed production CLI under the committed code identity.

## Recommendation boundary

The standalone report must state that historical screening cannot activate, deploy, schedule, or promote a rule, and that active state remains unchanged. Even `SURVIVES` permits only a newly frozen, explicitly approved forward phase.

## Final package review

Before approval, independently verify:

- exact artifact allowlist and no raw bars;
- canonical JSON/Markdown bytes and all hashes;
- zero-mismatch recomputation of classifications, all cash fields, partitions, metrics, diagnostics, and gates;
- separate **Evidence Integrity** and **Recommendation Quality** verdicts with P0/P1/P2 counts;
- no P0/P1 remains before the package is called final.
