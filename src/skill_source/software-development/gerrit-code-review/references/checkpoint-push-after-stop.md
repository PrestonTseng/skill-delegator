# Checkpoint push after a user-directed stop

Use this when implementation is in progress and the user says to stop expanding scope and push the current reviewable checkpoint to Gerrit.

## Procedure

1. **Freeze scope immediately.** Do not finish speculative follow-up work merely because it has started. Do not add more validators, refactors, or RED tests after the stop instruction.
2. **Return to the last coherent checkpoint.** Remove only clearly identified, just-added tests or edits whose implementation was not completed. Do not discard older requested work or reviewer fixes that were already part of the verified checkpoint.
3. **Run fresh gates after the rollback.** At minimum run the repository's full tests, lint/type checks, changed-file formatting check, and `git diff --check`. Do not cite gates run before removing partial work.
4. **Inspect the exact publish scope.** Review `git status --short`, the full staged file list, commit identity, executable Gerrit `commit-msg` hook, and existing `Change-Id` before committing.
5. **Preserve Gerrit identity.** Amend the existing commit when updating an existing change, retain its `Change-Id`, and push `HEAD:refs/for/<target-branch>`.
6. **Read back Gerrit metadata.** Confirm project, branch, status, patch-set number, revision SHA, and ref; require the Gerrit revision to equal local `HEAD`.
7. **Honor the stop after publishing.** Do not automatically create another patch set when a late reviewer reports findings. Report and record the findings, keep the code checkout unchanged, and wait for the user's review/direction.

## Async-review reconciliation

A reviewer dispatched before the stop may observe the checkout changing from an uncommitted diff to a committed patch set. Treat its scope warning as a timing/staleness note, not automatically as a code defect. Reconcile findings against the exact Gerrit revision:

- distinguish semantic findings from observations invalidated by the user-directed commit/push;
- independently verify push state through Gerrit readback if the reviewer lacked credentials;
- retain actionable findings in task evidence;
- do not silently fix or push them after the user explicitly took ownership of review.

## Pitfall

Do not leave newly written failing tests in the checkpoint just because they express desirable future hardening. A checkpoint sent for review must be internally coherent and backed by fresh execution evidence; preserve deferred tests/findings in task evidence instead.