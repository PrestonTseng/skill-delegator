# Expectancy Report Audit

Use this checklist when independently reviewing a trading, simulation, or shadow-order expectancy report reconstructed from immutable runs.

## 1. Pin three authorities separately

Record and fingerprint:

1. **Implementation authority:** repository HEAD and clean/dirty status.
2. **Report authority:** exact report bytes/hash; note whether tracked, ignored, or untracked.
3. **Evidence authority:** inclusive terminal run ID plus a deterministic path-and-file-digest stream for only the included run tree.

A report, HEAD, and evidence tree can change independently. If HEAD or report bytes move during review:

- stop using conclusions from the stale report;
- reread the final report;
- diff old and new HEAD to identify whether source/config changed or only the report changed;
- preserve the requested evidence cutoff even if later runs arrive;
- rerun computations affected by changed source/config/report claims;
- recheck all three fingerprints before issuing the verdict.

Do not silently mix a report from one revision, source semantics from another, and evidence totals from a third.

## 2. Reconstruct through an inclusive run cutoff

Some history APIs expose an exclusive `before_run` boundary. For a report claiming “through RUN_ID,” independently ensure the terminal run is included. Prefer validated canonical path keys, verify each included run, sort chronologically, then reduce with the production reducer. Confirm:

- first and last run IDs;
- completed/blocked counts;
- unique orders, resolutions, opens, exposure, and duplicates;
- every-row and aggregate cash reconciliation;
- later run count, proving later evidence was excluded.

## 3. Separate arithmetic truth from interpretation

Recompute exact Decimal totals and partitions first. Then audit narrative claims separately. Correct path counts do not prove statements such as:

- “primarily an entry-quality problem”;
- “post-TP1 management caused losses”;
- “an unsuitable regime caused fading losses.”

These are hypotheses unless a frozen, causal, replayed counterfactual isolates the mechanism. Replace causal prose with “motivates testing” or “is consistent with.”

For exit-path tables, compare classification from reported excursion fields with the economically implied fill path from gross PnL divided by initial risk. Excursion values may include same-bar prices that did not execute under stop-first ordering.

## 4. Audit denominator and label semantics

Require explicit definitions for every rate and cohort:

- **Signal retention** uses all first-observation classified signals.
- **Resolved retention** uses terminal outcomes and can be distorted by right-censoring.
- **Execution friction** is fees plus slippage.
- **Net cost drag** is fees plus slippage minus funding/financing offsets.
- **Event age from open** differs by one bar duration from age since completed-bar close.

Show empty bins when they explain discontinuities. A “current completed event” should identify whether age is measured from bar open or close.

## 5. Verify cohort causality

For every split—event age, side, MTF, date, session, stop size, regime—verify that membership was knowable and immutable at first observation. Outcome fields may score a cohort but must not define a purported entry-time candidate unless explicitly labeled a retrospective path analysis.

Check composition by day, side, and regime. A gross-positive but net-negative small cohort selected after inspecting several bins is hypothesis-generating, not “promising evidence” without qualification.

## 6. Review experiment design for internal consistency

Compare the detailed sequence with the executive recommendation. Common contradictions:

- claiming one-variable-at-a-time analysis while bundling freshness and volume;
- calling a router “independent” when it combines ADX, ATR, MTF, EMA, and a new strategy branch;
- saying combinations wait for standalone evidence while recommending a combined first package.

Every candidate needs its own versioned bytes/hash, start time, primary metric, failure rule, and unavailable state. Combination policies start a fresh evidence phase after constituent candidates pass independently.

## 7. Strengthen promotion gates for dependent samples

A row-count gate alone is inadequate for overlapping orders from one market stream. Require:

- minimum distinct UTC days or independently justified contiguous blocks;
- fixed OOS segment boundaries before outcomes are inspected;
- block-by-day/regime uncertainty rather than IID trade resampling;
- predeclared candidate family and thresholds;
- disclosure of every tested variant;
- an untouched confirmation phase after discovery;
- positive after-cost expectancy and PF as necessary, not sufficient, conditions;
- side/day/regime coverage and stress-cost results.

“Multiple-testing accounting” is too vague unless the method and candidate family are named.

## 8. Discovery-to-confirmation remediation pattern

When the arithmetic is valid but the proposed promotion plan bundles candidates or leaves multiple-testing controls vague, revise the plan into explicit phases:

1. **Freeze the discovery family.** Commit every candidate's exact formula, threshold, primary metric, failure rule, policy bytes/hash, and evidence start before new outcomes. Diagnostic boundaries are not extra candidate thresholds; choose one tested threshold per candidate.
2. **Annotate independently.** Multiple features may be computed on the same first observation for efficiency, but no candidate PASS decision may depend on another candidate. Keep entry-selection/regime candidates separate from paired exit-geometry families.
3. **Finish discovery with block coverage.** Predeclare minimum PASS/FAIL counts, distinct UTC days or regime blocks, and side/state coverage. These are review gates, not automatic promotion.
4. **Select at most one and reset.** If discovery is used to choose a candidate, freeze that one unchanged and set a new evidence cutoff. Discovery rows cannot count as untouched confirmation.
5. **Confirm on untouched blocks.** Predeclare terminal-outcome count, calendar coverage, fixed non-overlapping segment boundaries, block-bootstrap or other dependence-aware uncertainty method, base/stress cost criteria, effect-size requirement, drawdown comparison, and side/day/regime concentration checks.
6. **Defer combinations and routers.** Each component must pass its own untouched confirmation. A combination or regime router gets a new version/hash and another fresh evidence start; standalone evidence cannot confirm the combination.
7. **Require explicit approval.** No report, scheduler, or candidate automatically promotes a rule.

A useful finding disposition states exactly which sentence/formula/gate changed for every P0/P1/P2 item, preserves the original independent verdict, and explicitly says whether the original reviewer re-reviewed the revision.

## 9. Threshold and mechanism hygiene

- Do not label a gross-positive/net-negative small cohort “promising” after inspecting many bins. Say it motivates a frozen discovery candidate.
- Separate economic diagnostics from tested thresholds. For example, arithmetic solvency, target-payoff-to-cost, and cost-as-a-fraction-of-risk can imply different boundaries; report all diagnostics but preregister only one candidate threshold in a phase.
- A descriptive exit path can motivate either an entry or exit hypothesis but cannot distinguish them without paired replay.
- If a higher-timeframe PASS cohort is side-imbalanced, report signal and resolved composition before attributing any difference to the filter.
- When correcting a permissive filter, change only that filter. Leave event-local checks, trend rules, geometry, and other candidate decisions untouched until their own phases.

## 10. Verdict format

Provide:

- P0/P1/P2 counts;
- separate **Evidence integrity** and **Recommendation quality** verdicts;
- verified strengths, not only defects;
- exact reproduction outputs for key totals;
- initial/final report, HEAD, and evidence fingerprints;
- workspace impact and concurrent-change handling;
- explicit statement that later evidence was excluded from the pinned denominator.
