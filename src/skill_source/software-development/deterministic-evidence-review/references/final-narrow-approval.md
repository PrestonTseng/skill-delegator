# Final Narrow Approval Review Pattern

Use this after a prior independent review blocked approval on one or a few concrete integrity findings and a remediation commit claims closure.

## Scope discipline

- Pin the exact remediation range and HEAD; review that narrow diff rather than reopening implementation generally.
- Treat the prior review report as the closure specification. Enumerate every blocking finding, required adversarial case, and previously closed invariant that must not regress.
- Read the updated implementation/report plus exact changed source and tests. Do not modify implementation during an independent approval review.
- Preserve operational gates: approval for manual live verification does not imply approval for scheduling or cron.

## Boundary closure proof

For discovery-boundary confinement fixes:

1. Confirm `is_symlink()` is checked before `exists()`, `is_dir()`, filtering, or iteration at every relevant directory node.
2. Exercise both target states—an existing empty directory and a missing/dangling target—at history-root, partition/day, and run-entry levels.
3. Probe every consumer path that inherits the shared boundary, not only the low-level helper. Typical consumers include state reconstruction, aggregate/report generation, and publication/tick discovery.
4. Add a valid control: real empty directories and ordinary control files (for example, a regular lock file) must remain accepted.
5. Ensure no consumer can convert a rejected symlinked tree into a truthful-looking `verified: true` empty report.

## Verification ladder

Run fresh evidence in this order:

1. The focused adversarial regression selection.
2. The complete affected subsystem suites.
3. The full repository suite.
4. Compile/build, wrapper syntax/executable checks, and narrow plus cumulative diff checks.
5. A direct temporary-directory probe if the checked-in test matrix combines cases or does not visibly exercise every consumer/target-state pair.

If a probe script itself fails because of a wrong assertion or import path, correct the harness and rerun to a clean exit. Report only the successful evidence and any genuine product failure—not transient harness mistakes.

## Decision-ready artifact

Write the requested approval artifact with:

- exact reviewed range and HEAD;
- separate Spec and Quality verdicts;
- explicit Critical/High/Medium/Low findings, including `none`;
- closure evidence tied to source lines and consumer inheritance;
- a checklist reconfirming previously closed findings;
- fresh commands and observed test counts;
- a narrowly worded gate such as **approved for manual live verification only; cron remains a separate gate**.

If the destination is ignored or untracked, verify the file directly and mention that state so the controller can preserve it deliberately.