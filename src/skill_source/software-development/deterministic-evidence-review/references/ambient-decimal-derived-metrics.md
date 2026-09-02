# Ambient Decimal Context and Exact Derived Metrics

Use this note when deterministic financial or audit reports derive ratios, drawdowns, deltas, or other metrics from high-precision `Decimal` aggregates.

## Sign-only operations can round

Python `Decimal` unary arithmetic can apply the active context. In particular, `-value` may round a high-precision coefficient before a later exact-sum helper or explicit ratio context receives it. Moving the division into `localcontext(...)` does not recover digits already discarded by unary negation.

For transformations that should change only the sign or sign bit, use Decimal's non-arithmetic operations:

- `value.copy_negate()` instead of `-value`
- `value.copy_abs()` instead of `abs(value)` when coefficient preservation is required
- `value.copy_sign(other)` when copying a sign

Keep actual division in the contract's fixed context. Do not relax a strict validator or enlarge its half-ULP tolerance to accommodate builder-side premature rounding.

## High-risk derived-metric seams

Audit sign changes immediately before:

- profit-factor denominators or aggregate loss magnitudes;
- peak-minus-equity drawdown calculations;
- candidate-minus-baseline paired deltas;
- inputs to helpers advertised as exact or ambient-context independent;
- canonical serialization covered by golden bytes or SHA oracles.

## TDD regression pattern

1. Take real high-precision totals from the failing artifact or captured replay.
2. Construct fixtures without ambient-context arithmetic. Set reconciled cash fields directly rather than deriving them with `+` or `-` under the hostile test context.
3. Run the same production calculation under deliberately varied contexts, for example low precision with `ROUND_DOWN`, medium precision with `ROUND_UP`, and another precision with `ROUND_FLOOR`.
4. Assert one invariant output:
   - ratios match the fixed 28-digit or contract-defined context;
   - drawdowns preserve the exact equity magnitude;
   - tiny paired differences are not swallowed or inflated;
   - strict downstream validation accepts builder output.
5. Observe RED before production edits. Then replace only the sign operation and observe GREEN.
6. Retain all strict validation checks and existing byte oracles unchanged.

## Captured replay verification without an expensive rerun

When historical replay evidence is already captured and the defect is only in derived aggregation:

1. Deserialize the existing replay and rebuild the result; do not rerun the historical data pipeline.
2. Recursively find every summary-shaped mapping in the rebuilt result.
3. Pass every summary explicitly through the strict validator.
4. Run the complete renderer.
5. Record result/report byte lengths and hashes as verification evidence, but do not publish final evidence unless authorized.
6. Run the existing small fixed JSON/Markdown byte-oracle test unchanged to prove unaffected baseline bytes remain identical.

## Multi-hour production execution evidence

A successful reconstruction from a captured replay is not proof that the production wrapper can finish and publish. Long-running deterministic jobs also need durable process evidence:

1. Run the bounded production command through a tracked background process, not a subagent whose call/time budget may expire first.
2. Persist stdout, stderr, and the numeric exit code to named temporary files from the start. A watcher that only notices PID exit cannot recover a lost failure diagnostic.
3. Record explicit time/cutoff inputs and data-object hashes before execution, then verify them again afterward.
4. Treat an absent publication after process exit as a failure until stderr/exit evidence proves otherwise; do not infer OOM or application rejection without checking kernel and process evidence.
5. If a late failure forces one expensive diagnostic rerun, capture the replay object and pre-validation canonical result so arithmetic, rendering, and reviewer probes can iterate without repeating the historical computation.
6. Keep replay/cache captures under `/tmp`; only the authorized compact evidence package belongs in the repository.
7. After a clean fix commit, rerun the real wrapper. Intermediate reconstruction hashes are supporting evidence, not a substitute for commit-bound manifest publication and post-publication reread.

## Clean-worktree identity gates

Some artifact-producing CLI suites intentionally reject dirty tracked production/config state because the current Git identity is part of the evidence contract. If the full suite fails only on that guard while implementing an authorized change:

1. Run focused tests, compile checks, byte oracles, and diff checks before commit.
2. Review and commit exactly the authorized code/test paths.
3. Rerun the full suite from the clean committed worktree.
4. Report the pre-commit dirty-tree failure accurately; do not weaken the cleanliness guard or exclude those integration tests.

This is a sequencing requirement for identity-sensitive suites, not permission to skip pre-commit RED/GREEN evidence.
