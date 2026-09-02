# Shared normalized-validator remediation

Use this pattern when a downstream replay/report boundary duplicates validation already owned by an upstream loader, and a review requires both drift removal and restored behavioral evidence.

## Commit and evidence sequence

1. Add or update **tests only** and commit that snapshot before production edits.
2. Split the focused proof into two selections when they have different expected provenance:
   - **Already-correct behavior:** run separately and report honest immediate GREEN. Do not manufacture RED by reverting accepted production.
   - **Missing validator API/delegation:** run separately and require genuine RED caused by the absent public seam or absent delegation—not fixture/setup errors.
3. Commit production separately. Keep the test-only commit test-only and the production commit source-only.
4. Preserve exact commands, exit codes, counts, and failure reasons in the report.

## Pure validator extraction

Expose one public normalized-domain validator in the upstream data module:

- type-check the normalized bundle and policy/request inputs;
- require exact scored-bound equality;
- preserve compact caller-provided warmup bounds rather than silently expanding them;
- construct the canonical request through the upstream request builder;
- require exact frame/key iteration order when order is contractual;
- delegate bounds, chronology, identity, unit, volume, funding-slot, and recomputed source-hash checks to the unchanged authoritative validator;
- perform no cache, network, envelope, or raw-provider I/O.

Keep raw-provider evidence checks upstream when those fields are absent from the normalized typed bundle. A normalized validator cannot honestly revalidate discarded raw fields.

At the downstream boundary, call the public validator first, then return or consume the already-immutable tuple views. Delete duplicated duration tables, UTC helpers, numeric checks, bar validators, and funding validators. Keep only downstream-specific policy, execution, result-correlation, and presentation checks.

## Drift guards

Add all of these:

1. A compact valid normalized bundle accepted by the public validator.
2. Type-check probes for both public inputs.
3. Wrong scored bounds, wrong frame order, and tampered canonical source hashes rejected publicly.
4. Representative malformed inputs passed through both the public validator and downstream boundary.
5. A delegation sentinel: monkeypatch the downstream module's imported validator to raise and prove the public operation fails closed.
6. Canonical synthetic hashes computed by the same upstream series-hash function. Keep an explicit malformed-hash probe; do not replace meaningful hashes with repeated placeholder hex.

Validator extraction can legitimately change error wording to the authoritative upstream message. Update tests to assert the new exact stable message; do not broaden or delete expected-exception assertions.

## Restoring funding evidence

When strict slot coverage prevents arbitrary funding timestamps in an end-to-end fixture, use two complementary tests:

### End-to-end long hold

- Keep a valid full-coverage bundle.
- Hold baseline and candidate paths open across one valid funding slot strictly inside both holding periods.
- Assert exact nonzero projected funding and exact net PnL for fixed notional.
- Assert cash reconciliation.
- Assert caller cost quantity and funding events remain unchanged.
- This test must fail if downstream funding attachment is deleted.

### Focused boundary oracle

Exercise the downstream path/projection helper with distinctive rates at:

- exact entry — excluded;
- during hold — included;
- exact candidate final exit — included;
- exact baseline final exit — included for baseline;
- immediately after final exit — excluded.

Assert resolved timestamps and exact funding totals for both paths. Distinctive large excluded rates make accidental inclusion obvious.

## Final cumulative approval review

When the remediation is ready for independent approval, treat the earlier reports as a closure specification and verify the whole range, not only the latest commit:

1. Enumerate every original and re-review finding, then give each an explicit `Closed` or `Open` disposition with current code/test locations. Do not let the two latest findings hide previously closed invariants.
2. Reconstruct the tests-only validator selection from a disposable archive or worktree. A valid RED distinguishes the absent shared API/delegation from setup/import noise. Run already-correct funding tests separately and report honest immediate GREEN.
3. Independently recompute the fixed-notional funding identities rather than copying expected tuples from tests. Record the holding interval and prove a valid scored funding print lies strictly inside both baseline and candidate paths.
4. Run a mutation-sensitivity probe: temporarily remove downstream funding attachment at runtime and prove both funding and net-PnL identities change. This establishes that the restored test would catch the wiring regression.
5. For the boundary oracle, derive the included quantities/rates manually: entry excluded; mid-hold included using then-remaining quantity; each final-exit event included using pre-fill quantity; post-exit excluded. Check both exact cash and `resolved_at` timestamps.
6. Probe source-hash recomputation with a **valid-domain observation mutation** whose stored digest is left unchanged. If the mutation first violates OHLC/schema rules, it does not isolate hash recomputation.
7. Verify validator extraction structurally as well as behaviorally: compare the authoritative private validator's AST or exact source before/after production, inspect commit path scopes, and confirm loader/cache/raw-provider functions are untouched.
8. Use two delegation sentinels: one at the public validator's authoritative private core, and one at the downstream module's use site. The first proves real reuse; the second proves the public operation cannot bypass the shared seam.
9. Audit test weakening with semantic categories plus counts: test names, assertions, expected exceptions, fixture-hash replacements, regex narrowing, and replaced misleading tests. Rising counts support the review but never replace reading deletions.
10. Report scoped type-check success separately from accepted imported-module debt, and end with explicit Spec, Quality, and Critical/Important/Minor counts.

A private transient mapping around immutable tuple values is acceptable when it never crosses the operation boundary; state this explicitly rather than loosely claiming the entire returned structure is immutable.

## Test-diff audit

Before claiming no weakening:

- compare test function names across the accepted base and tests-only commit;
- inspect removed and added assertions, not just line counts;
- confirm every prior expected exception still exists;
- explain intentional strengthening (for example, broad regex replaced by exact authoritative messages);
- distinguish replacing a misleading zero-only assertion with stronger nonzero evidence from deleting a requirement.

## Verification ladder

Run and record:

1. funding-only selection;
2. validator/delegation-only selection;
3. complete downstream + upstream data test files;
4. required focused subsystem suite;
5. full suite with an exact collected/passed count;
6. compile/build over every modified file;
7. scoped type checking that separates modified-file cleanliness from accepted dependency/test debt;
8. diff checks, per-commit file lists, authorized total scope, final-newline checks, commit hashes, and clean status.

A quiet full-suite run that prints only progress dots proves exit status but not an exact count. Re-run without quiet output when the report requires the exact collected/passed number.
