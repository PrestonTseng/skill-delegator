# Independent detached-result recomputation

Use this recipe when a publication supplies a validated replay object plus deterministic JSON/Markdown artifacts, but the reviewer must not run a fresh provider replay or call the production result builder.

## Recompute independently

1. Pin and hash the replay object, publication artifacts, HEAD/tree, policy/config bytes, and any raw-cache envelope supplied by the controller.
2. Load the validated replay only in the repository's pinned environment. Treat pickle loading as trusted-input execution; never load an untrusted pickle.
3. Rebuild classifications directly from frozen first-observation geometry and policy bytes. Count one decision per canonical signal ID and verify exact signal/order/base/stress alignment before aggregation.
4. Reimplement exact finite-Decimal summation independently. Avoid ordinary chained `+`/`-` for high-precision cash identities: ambient Decimal context can round. Use a dynamically widened local context or exact Fraction/integer-coefficient arithmetic; use `copy_negate()` for exact sign changes.
5. Apply the documented fixed ratio context only to divisions. Recompute overall, side, segment, scenario, and state summaries; chronological drawdown must use the declared stable tie-break, normally `(resolved_at, signal_id)`.
6. Derive diagnostics and every screening gate/reason/status directly from recomputed evidence. Preserve frozen gate order and evidence-failure precedence.
7. Recursively compare the complete detached result tree and report the exact leaf mismatch count. A headline-only comparison is insufficient.
8. Re-render Markdown solely from the published JSON mapping and require byte identity. Verify canonical JSON bytes separately.

## Boundary evidence

Report how many natural observations land exactly on each inclusive threshold. If the count is zero, say so; do not imply the historical sample exercised the boundary. Pair the natural-data count with a tiny independent exact-Decimal control at `limit`, `limit + epsilon`, and each multi-limit corner.

## Publication-completeness review

Arithmetic equality does not prove the evidence package is self-contained. Compare the manifest to the binding design and require every promised provenance field, including as applicable:

- code commit plus the declared clean/dirty scope fingerprint;
- explicit provider, endpoint/request identity, market, and interval semantics;
- retrieval time and quality-check results;
- policy/config/source hashes;
- a commitment to the validated raw-cache/content envelope even when raw bars remain temporary;
- artifact hashes and exact publication inventory.

If these facts are recoverable only from a temporary cache or current CLI behavior, the detached publication does not preserve them. Classify the omission by decision risk; a design-required provenance gap is commonly P1 even when recomputation has zero numeric mismatches.

Also check ignored/untracked state explicitly: `git status` can look clean while an ignored publication directory is absent from the commit tree. State both facts.

## Reporting

Give separate Evidence Integrity and Recommendation Quality verdicts. State the exact mismatch count, P0/P1/P2 counts, strengths, blockers, and whether historical screening can authorize promotion. A standalone trading-screen report should explicitly say that historical screening cannot activate, deploy, schedule, or forward-confirm a rule.
