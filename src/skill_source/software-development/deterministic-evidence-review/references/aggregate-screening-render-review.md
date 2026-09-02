# Exact aggregate, screening, and renderer review

Use this reference for deterministic financial/research reports that expose a structured result builder plus a renderer accepting arbitrary mappings.

## Review the three boundaries separately

1. **Builder truth:** validated input rows produce exact summaries and partitions.
2. **Screening truth:** gates, counts, reasons, and status are derived from those exact summaries with frozen precedence.
3. **Renderer truth:** an arbitrary JSON-safe mapping cannot publish evidence that the builder could never produce.

A renderer that is deterministic and locally cash-reconciled can still be unsafe if it trusts contradictory parent/child evidence or screening conclusions.

## Profit-factor decision table

For terminal net cash:

| Positive cash present | Negative cash present | PF |
|---|---|---|
| yes | yes | positive sum / abs(negative sum) |
| yes | no | `INF` |
| no | yes | exact numeric zero |
| no | no | unavailable/null |

The last row includes empty, all-OPEN, and all-breakeven cohorts. Test all-loss separately; mixed, all-win, and empty fixtures do not cover it.

For comparisons, probe both operand positions across numeric zero, finite positive, `INF`, and null. Typical strict ordering is `INF > finite > 0`; equal values do not pass; null never passes.

## Aggregate reconciliation matrix

For every summary validate:

- `total = resolved + open`
- `resolved = wins + losses + breakeven`
- count fields are exact nonnegative integers, not bools
- cash identity is exact
- nullability/sentinels agree with counts and win/loss composition
- ratios and averages use the documented denominator and rounding context
- negative zero is normalized
- Decimal text has one canonical plain form and no exponent notation

For every evidence tree validate both side and segment projections against the parent. For candidate state partitions, reconcile every count and additive cash field across states to the candidate parent. Construction from shared rows is a strength, but a public renderer must independently reject contradictory serialized mappings.

### Derived-metric arithmetic under rounded Decimal output

Sign and sentinel checks are not enough for non-additive fields. A canonical-looking finite `average_winner`, `average_loser`, or `profit_factor` can still be mathematically impossible while all counts and cash reconcile.

When source rows are intentionally absent but summaries expose counts, exact net cash, rounded winner/loser averages, and rounded PF:

1. Parse canonical strings as `Decimal`; never convert through float.
2. Derive a half-ULP error bound from the exact ratio context. For precision `p`, a normal nonzero rounded value `x` has half-ULP `5 * 10 ** (x.adjusted() - p)`. Respect the context's subnormal floor with exponent `max(x.adjusted() - p, context.Etiny() - 1)`.
3. Convert each `Decimal` directly to `Fraction` for exact interval comparisons. Reconstruct gross-win and signed gross-loss centers by multiplying each average by its count, and scale each half-ULP bound by that count.
4. Require exact `net_pnl` to fall within the reconstructed-net interval. This catches non-sentinel average drift without inventing an arbitrary epsilon.
5. For mixed wins/losses, require PF ordering to agree with exact net: positive net implies PF above one, zero net implies PF exactly one, and negative net implies PF below one.
6. Independently derive a possible gross-win/gross-loss ratio interval from the rounded-average intervals. Require it to overlap the reported PF's own half-ULP interval. This rejects same-side-of-one PF fabrications that a sign-only rule would accept.

Use inclusive interval boundaries so legitimate `ROUND_HALF_EVEN` ties are accepted. Add a positive control with a genuine 28-significant-digit repeating result; hostile tests alone can accidentally codify an over-strict validator.

For coherent renderer RED, remember that the same scenario-wide summary may be duplicated in baseline and screening trees. Mutating only one copy can trigger an older identity check and does not prove derived-metric validation is missing. Mutate all required duplicate copies while preserving counts and cash, confirm the old renderer returns successfully, then add the validator and rerun the exact selection GREEN.

For paired evidence validate:

- `total_pairs = terminal_pairs + open_pairs`
- baseline and candidate summaries use the same terminal-pair subset
- side/segment pair counts reconcile to the parent
- duplicated expectancy/PF fields equal their source summaries
- mean delta equals exact candidate-minus-baseline net divided by terminal pairs under the documented ratio context

## Screening reconciliation

Do not merely validate that fields exist. Require:

- exact candidate order and exact per-candidate gate/count vocabularies
- gate values are actual booleans
- counts equal the referenced aggregate evidence
- failed reasons equal the false gates in frozen order
- evidence failures take the documented status precedence
- status is recomputed from gates, not trusted from input
- selected/complement states exactly match the candidate family

The strongest renderer check is to recompute the complete screening object from validated aggregate evidence and require exact equality. Perform that comparison only after independently validating the aggregate tree; otherwise the recomputation can faithfully derive a verdict from fabricated aggregates.

Translate concentration prose literally. “Not wholly concentrated in one segment” means resolved selected evidence spans at least two nonzero segments, not that every named segment must be nonzero. Keep this coverage gate separate from a performance gate such as “positive expectancy in at least two segments”: nonzero evidence and positive evidence answer different questions.

## Diagnostic reconciliation

Printed diagnostics are evidence, not decoration. Shape and canonical-Decimal checks are insufficient. Where derivable, require:

- available-decision distribution counts equal total decisions minus unavailable decisions
- zero count iff mean/median are null; positive count iff the printed statistics are non-null
- selected/pass count is no greater than total and equals the selected aggregate cohort
- retention rate equals selected count divided by total under the frozen Decimal context, with null only for a zero denominator
- execution-cost ratio count equals the corresponding scenario’s resolved count
- zero resolved count iff the ratio mean is null
- distance and cost statistics satisfy their nonnegative domain

When raw observations are intentionally absent from a detached result, do not pretend mean or median can be recomputed. Reconcile every identity the aggregate tree does expose, and enforce canonical nullability/domain rules for the rest.

## Adversarial renderer mutations

Starting from one valid builder result, deep-copy and mutate one property at a time. The renderer must reject:

1. child `total` changed without parent change
2. child cash changed while retaining local cash identity but breaking parent reconciliation
3. candidate parent changed while states remain unchanged
4. paired terminal/open/total count contradiction
5. paired child cash changed without parent/delta updates
6. duplicated paired expectancy/PF changed
7. mean delta changed
8. gate false with status `SURVIVES` and empty reasons
9. fabricated screening count
10. string/int gate value instead of bool
11. unknown/missing expected gate, count, reason, state, candidate, or hash field
12. exponent-form Decimal text such as `1E-20`

Record actual ACCEPTED/REJECTED output. Any accepted contradiction is an evidence-integrity blocker even if the ordinary builder output renders byte-identically.

Keep each mutation coherent in every dimension except the invariant under test. For example, when testing parent/child partition drift, preserve each child’s local cash identity and any cross-state equality so the RED failure cannot be satisfied by an older local validator. If a supposed RED case already raises for an unrelated reason, correct the fixture and rerun rather than counting it as coverage. Preserve the aggregate RED count, then run the exact same focused selection GREEN.

## TDD-history audit

- Pin the plan/spec clarification commit, all tests-only commits, and the source-only production commit.
- Prove source absence at the initial test commit with Git-tree inspection; isolate Python imports when reconstructing collection RED so a shared editable install cannot create false GREEN.
- Inspect deleted assertions individually. Schema-path corrections, exact-oracle corrections, and matrix expansion can be legitimate; threshold relaxation or removal is not.
- Tests committed before an absent API establish tests-before-production, but collection RED is weaker than behavior-specific RED. Report that distinction without inventing historical command output.
- Coverage is incomplete if adversarial probes find a defect not represented by an independent oracle, even when every committed focused test passes.
