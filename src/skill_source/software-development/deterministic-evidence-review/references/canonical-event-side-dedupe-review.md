# Canonical Event-and-Side Dedupe Review

Use this note when reviewing a replay that defines signal identity as a hash of strategy/version, market fields, event time, and side, then freezes the first observation.

## Identity construction

1. Write the identity tuple explicitly, including field order and normalization rules.
2. Verify emission and replay validation call the same canonical helper.
3. Require canonical UTC round trips for event time; equivalent offsets may normalize to one instant, but noncanonical text must not silently become a second identity.
4. Prove the serialization is injective over accepted inputs. Delimiter joins are unsafe unless the delimiter is rejected or escaped. For example, joining with `|` makes `(symbol="BTC|USDT", timeframe="5m")` indistinguishable from `(symbol="BTC", timeframe="USDT|5m")` when all other fields match. Prefer canonical structured bytes or length prefixes; when existing hashes must remain stable, reject delimiter-bearing fields.
5. Pair malformed probes with the real production confinement path. Upstream fixed market validation may prevent exploitation, but it does not make an ambiguous public canonical helper correct.

## Event+side ledger semantics

- One ledger key represents one canonical `(event, side)` identity.
- Same event time with opposite sides is two distinct identities when side is a binding field; do not classify it as duplicate leakage merely because timestamps match.
- Same identity with a later non-regressing observation is a repeat.
- Freeze the first signal geometry, order, and candidate/classifier output.
- Skip accepted repeats before order creation and classification so those side effects occur exactly once.
- Reject drift in static identity fields, canonical event time, schema, and frozen policy/semantic markers.
- Permit drift only in fields explicitly declared observation-dynamic.
- Enforce unique IDs and exact signal/order/decision/outcome alignment again in the result container.

## Test-quality trap after validator hardening

When production begins validating canonical hashes, revisit every older matcher test. A fixture such as `signal_id="event-a"` may become invalid before the intended mutation is examined. Then all negative assertions pass tautologically.

For every mutation matrix:

1. Construct a checksum-valid canonical baseline with the production helper.
2. Add a positive control: the unmodified later observation must match.
3. Mutate exactly one field.
4. Assert rejection for the intended reason or boundary.
5. Keep integration tests proving the repeat is skipped before order/classifier calls.

Do not count a broad `False` result as evidence unless the baseline itself is first proven valid.

## Evidence and reporting

- Separate semantic approval from empirical-count verification. A count of opposite-side same-event observations may be consistent with the contract while still being unverifiable without the final replay artifact or recorded scan.
- If instructed not to rerun tests or replay, inspect recorded evidence and label missing commit-specific results under **Cannot verify**.
- Verify packaged diffs using their exact context width before calling them stale; a package may be byte-identical to `git diff --unified=N` while differing from default context.
