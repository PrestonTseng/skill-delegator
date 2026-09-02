# Adversarial Probe Patterns

Use these patterns as recipes, not repository-specific tests. Build fixtures in a temporary directory and invoke the public aggregate or CLI.

## One-variable fixture rule

Start from a fully valid, checksummed immutable run. Change exactly one property, recompute its declared digest when testing semantic validation rather than checksum rejection, and preserve every unrelated invariant. This distinguishes a real boundary defect from a fixture rejected earlier for the wrong reason.

## Causal row probe

Create an in-window verified run whose row-level `observed_at` or equivalent event timestamp is later than run completion or reporting end. The aggregate must reject it or exclude it according to the binding attribution policy. Repeat for filter/decision rows; implementations often guard signals and outcomes but forget auxiliary evidence.

## BLOCKED/degraded contamination probe

Place otherwise-valid signal, outcome, and filter rows in a BLOCKED/degraded run. Expected policy is commonly:

- tick/status/blocker contributes to operational evidence;
- strategy signals, outcomes, PnL, and filter-performance rows do not contribute;
- the event ledger still identifies the blocked run.

Verify each channel independently.

## Artifact symlink probe

Keep the run directory itself real. Replace one machine artifact with a symlink to a temporary file outside the configured root, update the manifest digest to match the external bytes, and run verification. Repeat for manifest and human-review artifacts. A name-set check plus `is_file()` is insufficient because both can follow symlinks.

## Discovery symlink probe

Per-run verification cannot protect nodes that discovery never emits. Exercise the public reconstruction and reporting consumers against this matrix:

1. history root (`runs`) symlink to an empty external directory;
2. history root symlink to a missing target;
3. day symlink to an empty external directory;
4. day symlink to a missing target;
5. run entry symlink to a missing target;
6. populated root/day/run symlinks as a separate matrix.

Every symlink case must fail explicitly before `exists()`, `is_dir()`, name filtering, or iteration can follow or silently ignore it. Then prove the negative controls: a real empty `runs` tree, a real empty day, and ordinary control files such as a lock file remain accepted. Run the same matrix through each public consumer that inherits shared discovery so a false `verified: true` empty aggregate cannot reappear.

## Aggregate numeric-domain probe

Choose individually accepted numeric values whose exact sum exceeds the accepted aggregate coefficient/exponent domain. Verify that the final aggregate is rejected after exact arithmetic. Run under a hostile ambient decimal context to ensure behavior does not depend on process defaults. Include exact zero and cancellation cases.

## Transition probes

Exercise these histories separately:

1. signal first observed before window, repeated in window;
2. pre-window OPEN, first RESOLVED observation in window;
3. prior RESOLVED repeated in window;
4. resolution event time before window but first verified observation in window;
5. two distinct signals with identical event timestamps;
6. future canonical run at `end` containing malformed bytes that must remain unopened.

Assert both summaries and event-ledger identities.

## Denominator and scope probes

For a non-24-hour window, assert every rate or normalized frequency exposes numerator, denominator, and unit. Check inter-event interval sample count is `max(event_count - 1, 0)`. Keep supporting-history verification counts separate from in-window run/health counts.

## Read-only determinism probe

Run the explicit-window wrapper twice in a clean environment, compare stdout byte-for-byte, parse it as the declared format, and hash it. Independently hash the evidence tree before and after if the task requires mutation proof. Keep output files outside the repository.

## Run-ID and cutoff probes

When cutoff filtering must avoid opening later artifacts, first establish what path metadata is authoritative. If a run ID encodes only whole seconds, require the run manifest timestamp to be whole-second as well; otherwise two valid runs in the same path-second cannot be ordered without opening manifests. Test both lexical-order disagreement directions and same-second suffix ordering. A malformed canonical run after the cutoff must remain unopened, while malformed evidence required before the cutoff must fail closed. Fractional signal/outcome event timestamps can remain valid when the run-publication timestamp contract is whole-second.

## Scheduler and clean-shell integration probes

Do not rely only on subprocesses launched from pytest: test configuration may inject `src` into `PYTHONPATH` and hide a broken production wrapper. Invoke the real wrapper from a clean environment (for example `env -u PYTHONPATH ./scripts/job.sh --help`) and verify:

- src-layout imports work outside the test runner;
- timeout syntax is accepted by the installed implementation;
- timeout plus kill grace is below the scheduler's hard limit;
- no-event stdout is exactly zero bytes;
- failures are nonzero and emit no false success event;
- a process-level nonblocking lock permits only one publication;
- runner-return paths are canonical, newly published, confined, and non-symlinked.

## Record identity versus delivery semantics

Exactly-once immutable event identity does not imply exactly-once Discord/email/chat delivery. Without a transactional acknowledgement from the external channel, classify immediate notification truthfully as best-effort or deliberately at-least-once with possible duplicates. Include stable event IDs and make deterministic periodic reconciliation authoritative. Do not add an unacknowledged local `delivered` cursor: a crash between cursor mutation and external delivery can permanently suppress an event.

## Reporting snippet

For each confirmed defect record:

- severity and short title;
- exact file/line range;
- binding requirement;
- minimal fixture mutation;
- actual output/error;
- why existing tests missed it;
- concrete remediation and regression test.
