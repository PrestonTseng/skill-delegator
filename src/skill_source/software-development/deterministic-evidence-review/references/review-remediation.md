# Review Remediation Reference

Use this after an independent review rejects a deterministic evidence reader or aggregate.

## Finding-to-regression matrix

| Risk class | Minimum focused regression |
|---|---|
| Path confinement | Symlink each ancestor (`runs`, day, run) and each required manifest/review/artifact to checksum-identical bytes outside the root; every case must fail before evidence use. |
| Causal/PIT | Future run remains unopened; malformed supporting prior state fails; every parsed row timestamp is no later than run completion; BLOCKED strategy/filter rows do not enter performance metrics. |
| Lifecycle | First signal, duplicate, initial OPEN, OPEN→RESOLVED, terminal replay, terminal conflict/regression, and same-time distinct signals. |
| Arithmetic | Hostile ambient Decimal context; empty sum; exact zero; two individually valid values whose exact sum exceeds the accepted aggregate domain; exercise notional and every cash label. |
| Statistics | Zero samples, breakeven partition, explicit numerator/denominator, non-24-hour normalization, nonterminating deterministic rounding, equal timestamps/zero intervals, scoped supporting versus in-window counts. |
| Compatibility | Existing published runs verify and reconstruct in a read-only probe after hardening. |

## Shared reducer shape

Prefer one pure function over parallel consumer reducers:

```text
reduce_verified_runs(chronological_runs) -> {
  final_state,
  signal_observations: FIRST | DUPLICATE + run/observation metadata,
  outcome_transitions: OPEN | RESOLVED + previous status + origin/observation metadata
}
```

The reducer owns identity, deduplication, chronology, terminality, projection, and final reconciliation. A daily/report consumer filters emitted transitions by run observation time and formats metrics. It must not reimplement those state transitions.

## Evidence sequence

1. Add all focused regressions.
2. Run focused tests and save genuine behavior failures (RED).
3. Implement shared-seam fixes.
4. Run focused tests (GREEN).
5. Run target-adjacent suites, then the full suite.
6. Run compile/build, shell/wrapper checks, and diff checks.
7. Run a read-only compatibility probe over existing evidence with the real import path/environment.
8. Append report evidence, rerun fresh final verification, then commit.

Do not turn a transient import/setup mistake into a product finding. Fix the invocation and record the successful production-shaped command.
