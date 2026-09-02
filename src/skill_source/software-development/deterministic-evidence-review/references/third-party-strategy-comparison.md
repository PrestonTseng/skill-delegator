# Third-party strategy archive comparisons

Use this when a user supplies a strategy archive and asks why its reported performance differs from an audited trading pipeline, or asks for an apples-to-apples historical comparison.

## 1. Pin what the archive can actually prove

Fingerprint the archive and inventory source, tests, runners, raw evidence, reports, dependency locks, and pipeline entrypoints. Keep three claims separate:

- **documented strategy**: prose or comments describe intended behavior;
- **executable strategy**: the supplied files can reproduce signals and outcomes;
- **reported performance**: raw logs and deterministic code can reproduce the stated totals.

A README hit rate is not performance evidence when the archive omits its history, runner, or report inputs. Do not silently reconstruct missing bytes and call the result a reproduction.

## 2. Audit the scorer before comparing strategies

Probe whether the third-party scorer preserves executable order semantics:

- stable signal/event identity and deduplication;
- entry fill before outcome scoring;
- complete chronological OHLC path rather than sparse horizon snapshots;
- mutually exclusive terminal outcomes and explicit same-bar ordering;
- notional/quantity and partial exits;
- fees, slippage, funding, and exact net-cash reconciliation;
- OPEN/right-censored outcomes;
- point-in-time completed-bar inputs.

Useful adversarial fixtures include:

- a path that touches TP and SL in different orders;
- sparse history where the nearest-before price predates the signal;
- duplicate observations of one market event;
- invalid LONG/SHORT stop geometry;
- a signal whose entry never fills;
- post-cutoff data that would reverse the decision if leaked.

Quote actual probe output. A scorer that can report both 100% TP and 100% SL rates is measuring nonexclusive excursions, not trade outcomes.

## 3. Choose an honest comparison boundary

Prefer the narrowest common executable seam:

1. freeze the audited baseline signals and first-observation geometry;
2. express the external rule as a pure pre-entry classifier or one paired counterfactual;
3. apply it to the same unique signals;
4. keep orders, market, interval, notional, costs, funding, bars, and resolver identical;
5. partition baseline into PASS/FAIL/UNAVAILABLE and reconcile counts plus cash exactly.

If the external archive cannot reproduce its full system, name the result after the tested rule (for example, “distance-filter cohort”), not after the whole vendor/system. Explain plainly that this tests whether the supplied rule improves the audited baseline; it does not reproduce the missing system.

## 4. Freeze before outcomes

Commit or fingerprint before running:

- exact half-open scored interval and warm-up;
- market/provider identity;
- classifier formula and inclusive/exclusive boundaries;
- invalid/unavailable behavior;
- base and stress costs;
- sample/segment/side coverage gates;
- survival criteria;
- every tested variant.

For a committed canonical rule, freeze identity with a test that asserts the **exact known SHA-256 digest** of the committed bytes. Checking only that a digest is 64 hex characters, or only that serializer output round-trips, can still bless the wrong policy bytes.

Never inspect outcomes and then add an economically convenient floor, cap, side split, or combination without declaring a new candidate family and multiple-testing consequence.

### Preserve overlapping clauses without overstating attribution

A supplied filter may contain several thresholds that are partly or wholly redundant under the audited strategy's geometry. For example, a TP1-distance cap can add no effective selection when TP1 is deterministically derived from the stop distance and the stop cap is already tighter.

For a faithful first screening:

1. keep every supplied clause verbatim, including its exact boundary operator;
2. record each raw scalar and clause-level reason code before computing the combined decision;
3. report marginal exclusions for each clause and for their intersection;
4. state explicitly when a clause is mathematically or empirically redundant in this baseline;
5. attribute the result only to the frozen compound rule, not to one component;
6. if component attribution matters, register each isolated clause as a new OVAT candidate before inspecting its outcomes.

Do not delete a redundant-looking clause after seeing data, and do not quietly add a cost-motivated lower bound to a supplied upper-cap rule. Either change creates a different hypothesis.

## 5. Report the gap in two layers

First provide a high-school-level strategy comparison:

- what market condition each strategy looks for;
- what triggers entry;
- which filters are intended versus actually executable;
- how stop/targets are set;
- how performance is scored.

Then provide the audited result:

- baseline versus tested PASS cohort;
- retention, resolved, OPEN, side, and segment counts;
- gross, costs, funding, net, expectancy, PF, drawdown;
- base/stress results;
- evidence-integrity and recommendation-quality verdicts.

The most important plain-language distinction is often **strategy difference versus measurement difference**. A gross retrospective TP hit rate can look much better than unique-order, path-aware, after-cost PnL even when the underlying entries are the same.

## 6. Approval boundary

Historical survival only permits a fresh forward phase. It never authorizes active-shadow filtering, live capital, scheduler changes, chart mutation, combinations, or automatic promotion. Keep those actions behind explicit approval and a new evidence cutoff.
