# Point-in-Time Trading Screening Backtests

Use this pattern when an immutable shadow-trading review produces candidate entry, regime, or exit hypotheses and the user authorizes historical replay for rapid validation.

## Purpose boundary

A historical screening backtest may:

- reject a candidate quickly;
- expose data/provenance defects;
- estimate sample frequency and side/regime concentration;
- justify continued forward observation.

It may not:

- count as untouched forward confirmation;
- authorize automatic promotion;
- justify a combination/router from individually tested features;
- erase or rewrite immutable forward evidence.

State this boundary in the design, report, and canonical task record.

## Freeze before fetching outcomes

Commit or otherwise fingerprint:

- half-open scored interval;
- warm-up requirements per timeframe;
- fixed chronological reporting segments;
- complete candidate family, one threshold per candidate, and unavailable rules;
- base/stress costs, funding, notional, stop/target ordering, and censoring policy;
- screening failure/survival rule;
- source/provider identity and output schema.

Diagnostics may show several economic boundaries, but only one threshold belongs to a candidate version. Never search a threshold grid and present only the winner.

## No-lookahead replay contract

At each evaluation cutoff:

1. Expose only bars completed at or before the cutoff.
2. Run the unchanged baseline evaluator with production frame limits and current-price semantics.
3. Deduplicate using production signal identity; the first verified observation freezes order geometry and all candidate annotations.
4. Compute candidates independently. Computing several annotations in one pass is efficient; making one PASS depend on another violates OVAT.
5. Resolve outcomes only from later completed bars under production same-bar ordering, costs, funding, and right-censoring.
6. Fail the historical replay on scored-window gaps, invalid OHLC, non-monotonic data, provenance/policy drift, future cutoffs, or cash mismatch. Do not silently skip bad intervals.

Missing candidate-only data in live shadow observation should emit `UNAVAILABLE` without blocking baseline; that is distinct from a corrupted historical replay.

## First-observation deduplication and mutable diagnostics

Event identity and observation evidence are different contracts. A source can emit the same event at several cutoffs while recomputing current geometry or diagnostics. Historical replay must freeze the first verified observation without either creating duplicate orders or falsely requiring every later observation field to remain byte-identical.

- Centralize canonical signal-ID construction in one source helper and use it both when emitting and when validating replay evidence. Recompute the expected ID from its declared immutable components; do not duplicate the hash formula in the replay.
- Key deduplication by the complete canonical ID defined by policy. Never substitute a convenient subset such as `event_time` alone. If direction is part of the ID, the same event time with the opposite side is a distinct signal, not a duplicate conflict.
- Apply duplicate matching only after the full ID has matched. Require monotonic observation time plus exact strategy/version, symbol, timeframe, side, schema, canonical event time, and static source semantics.
- Partition diagnostics explicitly into static identity/provenance fields and dynamic observation fields. Permit drift only for an enumerated dynamic set; reject missing, duplicated, reordered, mistyped, or unknown keys and any static-field drift. Do not solve a real-data conflict by dropping the entire diagnostics comparison.
- Keep global live/shadow reducers unchanged when their contract legitimately treats all diagnostics as immutable. Use a replay-specific matcher when the historical source contract differs.
- Freeze the first signal, order geometry, and candidate decisions. Accepted repeats must never overwrite them or reclassify the candidate.
- Before publication, scan the real immutable cache and report: first observations, repeats, accepted dynamic drifts, canonical-ID mismatches, static conflicts, and the first conflict example. A scan that groups by a narrower key than production identity can manufacture thousands of false conflicts, so verify the grouping key itself with opposite-side and same-time controls.

Minimum adversarial tests:

1. same canonical ID with allowed dynamic diagnostic/geometry drift preserves byte-identical first evidence;
2. same ID with event-time, side, semantics, schema, or chronology drift fails closed;
3. canonical fields whose recomputed hash does not equal `signal_id` fail closed;
4. same event time with a different side and correctly recomputed different ID creates a distinct first order when side belongs to identity;
5. the global live/shadow duplicate matcher retains its original stricter behavior.

## Candidate family separation

Keep these as different experiment families:

- entry/selection filters;
- regime annotations;
- paired exit-geometry counterfactuals;
- portfolio-concurrency policies;
- strategy routers or new strategy identities.

A paired exit replay keeps entry, bars, targets, quantities, costs, funding, and ordering identical and changes exactly one exit-state transition. Report paired net-PnL delta and path changes, not only standalone PF.

Combinations and routers are deferred until constituent policies independently pass untouched confirmation. They then receive new bytes/hash and a new evidence start.

## Data and artifact discipline

- Keep large raw market history in temporary/cache storage, not Git.
- Persist provider/retrieval metadata, source content digests, quality checks, exact policy bytes/hash, aggregate JSON, segment/side partitions, and a readable report.
- Include every evaluated candidate and failure; never publish only survivors.
- Report unresolved end-window orders explicitly.
- Reconcile gross, fees, slippage, funding, and net exactly.

## Unit and projection provenance

Trace economic units through every layer before implementation planning. A production pipeline may resolve a core outcome at one contract/unit and only later project it to a fixed shadow notional; a backtest that reports the core cash as the portfolio cash can reconcile perfectly while being economically wrong.

- Identify the authoritative order/notional projector and outcome projector before writing the replay plan.
- Reuse the production sequence exactly: create the fixed-notional order, resolve the core path with its frozen quantity semantics, then project every cash field through the existing outcome projector.
- Do not substitute a new per-signal quantity formula when production already has a hardened projection layer.
- Record both the core quantity convention and final reported notional in policy/manifests.
- Test gross, fees, slippage, funding, and net after projection; require exact reconciliation and verify that no unscaled core cash is labeled as fixed-notional evidence.
- Include this unit-flow trace in pre-flight plan review. Treat ambiguous terms such as `quantity`, `notional`, and `outcome` as unresolved until their layer and units are named.

## Replay-engine implementation review

When reviewing the replay implementation rather than only its aggregate report, probe the seams that happy-path integration tests often miss:

### Result-contract closure

A frozen result dataclass is not trustworthy merely because its fields are tuples. Construct malformed records directly and require rejection of:

- missing, duplicated, or reordered candidate decisions;
- decision IDs, policy hashes, or observation cutoffs that do not match their signal;
- baseline/order/outcome count or signal-order drift;
- paired legs with matching signal IDs but the wrong cost scenario;
- paired baselines that are not exactly the corresponding reported baseline outcome.

For a fixed candidate family, validate the exact decision count and canonical order per signal. Downstream aggregation should not have to rediscover whether replay evidence is structurally complete.

### Public input validation

Do not assume that a bundle is valid just because the normal loader validates it. If its public record type is directly constructible, either carry unforgeable validated provenance or revalidate at the replay boundary. Use otherwise-valid adversarial probes for:

- one missing scored bar, overlap, duplicate, or wrong frame duration;
- rows outside the declared warm-up/scored bounds;
- empty or incomplete historical funding;
- invalid retrieval/collection identity;
- valid monotonic data that is nevertheless non-contiguous.

A replay that returns an empty result for a corrupted history has failed open. Distinguish candidate-local `UNAVAILABLE` from historical-feed invalidity.

### Honest historical availability projection

Live evaluators may reject batch-retrieved historical rows because `retrieved_at` is after the simulated cutoff. Derived copies with availability set to bar close/event time are acceptable only when all of these hold:

- raw bundle objects and original provider retrieval timestamps remain untouched;
- source bytes/hashes still bind the original data;
- projected timestamps are private hypothetical availability metadata, not provider provenance;
- no projected retrieval field is serialized or echoed into durable source evidence;
- helper names/docstrings state the distinction explicitly.

Prefer a dedicated replay-view type when projected metadata could escape through evaluator outputs. Trace signal diagnostics and candidate source-cutoff fields to verify that only honest event/close cutoffs are published.

### Scaling review

A binary search followed by `bars[index:]` is not automatically efficient: tuple/list slicing copies the entire tail. Inspect all downstream resolvers for additional `list(...)` conversions and repeated base/stress or paired scans. With many OPEN or late-resolving signals, this can become O(signals × remaining history) time and allocation even though cutoff indexing itself is linear.

Prefer a frozen indexed `Sequence` view over one immutable backing tuple, storing only a start index, or use a `(bars, start_index)` resolver API. View construction must itself be O(1): do not scan the backing tuple for element validation on every signal. Widen existing resolver annotations and input validation to consume `Sequence[Bar]` directly, and remove eager `list(...)` materialization without changing execution order, stop-first rules, funding boundaries, OPEN behavior, or cash arithmetic.

Use structural and semantic evidence together:

- create many suffix windows and assert that all share the identical backing tuple and only their start indices differ;
- compare list, tuple, and indexed-view outcomes for resolved baseline, OPEN, and paired/alternate resolver paths;
- use a custom counting `Sequence` to prove direct consumption, while accounting for the inherent validation traversal and path traversal in the expected count;
- report window allocation as O(signals), while naming any per-signal path scans that remain semantically necessary.

Share resolver traversals only where semantics permit; do not overengineer a batch resolver merely to remove copying.

### No-lookahead test quality

A post-cutoff mutation test is weak when a monkeypatched source manufactures signal geometry only from `as_of` and ignores the supplied frames. Pair two proofs:

1. capture evaluator arguments and assert every bar/funding observation is bounded by the cutoff; and
2. make the fake source derive geometry from the latest supplied completed bar, or use a real-source causal fixture, so source signal/order equality is not tautological.

Candidate decisions should use the real candidate implementation, include a future value that would reverse the result if leaked, and allow future outcome changes while first-observation evidence remains unchanged.

### Test-first history verification

For claimed RED/GREEN history, inspect the tests-only commit and the later test diff rather than trusting a report. A disposable `git archive` of the tests-only commit can independently reproduce collection or behavioral RED without modifying the reviewed worktree. Compare test names, assertion counts, and expected-exception calls across the production commit; typing-only or fixture-validity adaptations are acceptable, but removed/weakened behavioral assertions are not.

When stricter public-boundary validation makes an old synthetic bundle invalid, repair the fixture in the tests-only phase before recording RED. Derive one compact aligned policy/bundle range, generate exact complete coverage for every timeframe from those bounds, use the provider's actual interval-close semantics and retrieval/collection identity, and generate every required funding slot. Preserve the outcome oracle by moving path/event values across the first cutoff rather than weakening expected cash or candidate decisions. If no compact valid fixture can satisfy both the accepted policy and the proposed coverage contract, stop and report the conflict instead of adding a validation bypass.

A valid strict sequence is:

1. keep accepted semantic tests green under the corrected fixture;
2. add the complete finding-to-regression matrix;
3. run RED until failures correspond only to missing findings, not collection or unrelated fixture errors;
4. audit that the checkpoint changes tests only and commit it;
5. implement production, run targeted/focused/full GREEN, and audit the exact post-checkpoint test diff;
6. report any unavoidable GREEN test-helper edit explicitly and prove it changes fixture validity or typing only.

## Screening interpretation

Predeclare minimum resolved, PASS/FAIL, side/state, and time-block coverage. Require positive after-cost expectancy and PF under base costs, positive behavior across fixed chronological segments, non-negative stress results, and no single-side/single-segment concentration before calling a candidate a survivor.

A survivor is only eligible for a fresh forward phase. Discovery selects at most one candidate, freezes it, resets the evidence cutoff, and starts untouched confirmation with day/regime-blocked uncertainty. Failure rejects that version; it does not prove the mechanism can never work.

## Plain-language decision summary

After the technical report, explain the result to a non-specialist in three short sections:

1. **Current state:** what is losing/working and what remains unknown.
2. **Next action:** what will be recorded or replayed, emphasizing one-variable-at-a-time and no real trading.
3. **Approval requested:** one sentence naming the reversible scope being authorized and a short list of actions that remain forbidden.

Use only the few numbers needed for the decision. Do not make the stakeholder reread the full audit in simplified words.
