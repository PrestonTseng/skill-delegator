# Bounded Delegated Review Operations

Use this pattern for long implementation tasks executed by fresh workers and independently reviewed in several waves. The aim is to preserve rigor without turning review into an unbounded search process.

## Canonical task state

Record outside chat:

- exact objective and authorization source;
- active bounded task and non-goals;
- base/HEAD commits and worktree path;
- acceptance criteria and prohibited effects;
- findings still open versus independently closed;
- review/fix budget and explicit stop gate;
- next exact verification action.

After context compaction or an asynchronous result, reconcile the latest user intent with this record before resuming. A background completion is an inbox item, not authority to override a newer topic or stop instruction.

## Worker handoff and continuation

Treat a worker report as a claim, not proof.

1. Inspect `git status`, tracked plus untracked scope, commit range, and `git diff --check`.
2. Read changed shared seams and the focused tests before editing.
3. If a worker hits a tool/turn limit with useful uncommitted work, preserve it and dispatch a continuation worker with the exact current state. Do not restart or discard by default.
4. Require the continuation to resolve unfinished/dead API edits, write the correct task report, run fresh gates, and commit.
5. Before writing a generic task report, run `git ls-files --error-unmatch` for that path. Never append a later task's evidence to an inherited tracked report. Put task-specific evidence in the correct namespaced or task-numbered report.

## Parent verification truthfulness

Run gates in an order that makes partial execution explicit:

```text
lock/sync
→ runtime version
→ format check
→ lint
→ focused tests
→ full tests
→ compile/build/package checks
→ diff/status
```

A chained command that stops at formatting proves nothing about later gates. Report later gates as **not run**, not passed. If the worker claimed a gate passed and fresh evidence disagrees, correct the report and rerun from the failed gate after the fix. Never carry forward an old test count across a final edit.

## Review loop budget

Use four distinct phases:

1. **Initial task review** — broad spec and quality review of the complete task package.
2. **Coherent fix wave** — send all Critical/Important findings from that review to one fresh fixer; prefer a shared root-cause repair over finding-by-finding patches.
3. **Focused closure review** — verify only the original findings and changed-line regressions. Do not reopen unrelated, independently closed behavior.
4. **Final stop gate** — if the closure fix itself introduced concrete changed-line defects, allow one final bounded fix and review only those defects plus cumulative scope cleanliness. Explicitly prohibit new unrelated audit areas.

Provider refusal or safety filtering is not a verdict. Narrow the prompt to local correctness, temporary fixtures, and exact bounded behavior, then retry once with materially clearer context.

## Separate production closure from regression quality

Always issue and track two decisions:

- **Production defect closure**: does the implementation now satisfy the behavior?
- **Regression quality**: do committed tests deterministically reach and prove the required interleavings?

Production may be approved while regression quality is rejected. In that case, make a tests-only fix and do not reopen approved production behavior. Guard against unreachable checkpoints: prove the intended boundary was reached (for example, both targets promoted before a multi-target rollback failure), not merely that the test passed.

## Filesystem transaction probes

For local transactional reconcilers, deterministic tests should cover:

- retained root/namespace directory descriptors and inode identity;
- replacement of lock namespace and target root;
- same raw symlink target with a different inode during rollback;
- backups retained through every rollback-capable phase;
- metadata publication as the commit boundary;
- post-commit cleanup failure preserving committed links and metadata;
- initially absent root restored exactly on pre-commit failure;
- multi-target rollback after all intended promotions are demonstrably reached;
- replacement paths remaining untouched.

See `transaction-identity-lifecycle-closure.md` for the detailed matrix.

## Receipt/provenance probes

For verification receipts:

- hash config inputs through descriptor-relative no-follow traversal;
- attach a Git commit only when its ordinary blobs exactly equal the bytes hashed;
- verify every desired source independently so target-scan failure cannot hide source tamper;
- require schema plus semantic coherence for exact filename sets, source identity types, counts, and converged evidence;
- make the public publication result atomic: a reported failure leaves no newly published receipt, while success may retain it.

See `config-receipt-provenance-review.md` for the detailed matrix.

## Closure record

A task closes only when:

- parent fresh gates pass on final HEAD;
- production closure and regression quality are both approved;
- cumulative scope contains no misplaced prior-task reports or prohibited files;
- the canonical ledger/status names the endpoint commit, real test count, limitations, and next gated task.
