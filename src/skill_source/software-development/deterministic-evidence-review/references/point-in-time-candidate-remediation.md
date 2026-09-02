# Point-in-Time Candidate Remediation

Use this checklist when review findings concern independent point-in-time decisions built from bars, diagnostics, and precomputed overlays.

## Regression matrix

| Boundary | RED cases | Required result |
|---|---|---|
| Bar integrity | Each OHLC field at zero and negative; retrieval just before close | Global `ValueError`, never candidate-local `UNAVAILABLE` |
| Diagnostic chronology | Event time at cutoff and cutoff + 1 microsecond | Equality follows policy; future diagnostic raises globally |
| Public completion helper | Open/live bar, future close, retrieval before close | Helper enforces its advertised cutoff/completion contract directly |
| Overlay precedence | Malformed frame before future frame and reversed insertion order | Both permutations raise for future evidence |
| Overlay identity | Mismatched top-level identity mixed with malformed optional fields | Identity corruption raises before schema availability handling |
| Positive overlay audit | Positive outcome with count > 0 and no cutoff, unsupported trend, count/trend mismatch | Candidate-local `UNAVAILABLE`; positive result cannot survive inconsistent evidence |
| Local insufficiency | Zero denominator, missing provider value, malformed overlay field | Preserve every truthful count, raw scalar, and contributing cutoff |
| Typing | Audit payload construction | Use the contract's immutable scalar/key-value aliases; do not silence mismatches with `type: ignore` |

## Two-phase overlay pattern

1. **Global scan:** inspect every present identity and every present timestamp, independent of mapping order or unrelated schema defects. Reject noncanonical/future timestamps and identity corruption.
2. **Candidate classification:** only after the scan, validate required keys, decision vocabulary, frame schema, and count/time/trend invariants. Schema insufficiency may return local `UNAVAILABLE`.
3. **Canonical audit extraction:** use one extractor for success and every early-unavailable path. Record per-frame trend, count, and close cutoff plus any useful aggregate cutoff. Emit `None` only for unusable or absent scalar evidence.

Do not stop scanning at the first malformed frame: an early local return can hide future evidence later in the mapping.

## TDD and closure evidence

- Build the complete finding-to-regression matrix before production edits.
- Run it once and retain aggregate RED counts.
- Make shared-boundary fixes rather than patching individual candidate branches.
- Run focused tests, adjacent subsystem tests, the full suite, compile/build, static typing when relevant, and diff checks.
- Before commit, verify the staged path list exactly matches authorized scope.
- Append a finding-by-finding disposition, RED/GREEN evidence, commit, and concerns to the existing implementation report.
