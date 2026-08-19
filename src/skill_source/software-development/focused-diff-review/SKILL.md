---
name: focused-diff-review
description: Use when reviewing an uncommitted/current code diff with a specific lens such as async safety, efficiency, listener cleanup, error propagation, races, or simplification, especially when the user says not to modify files.
---

# Focused Diff Review

## Overview

Review the live diff through the user's requested lens. This is not a full PR workflow: stay focused, inspect enough surrounding code to validate safety claims, and do not edit files unless the user later asks.

## Workflow

1. Establish the current diff shape: `git status --short`, `git diff --stat`, `git diff --name-only`, then read the relevant hunks.
   - `git diff` does not include untracked files. Enumerate them with `git ls-files --others --exclude-standard`, read every in-scope untracked source/test file explicitly, include them in the review and test selection, and run `git diff --no-index --check /dev/null <file>` (accepting its normal “differences found” exit) when final whitespace validation must cover them.
   - Treat the index, working tree, and `HEAD` as three distinct mutable snapshots. Record the initial `HEAD`, inspect `git diff --cached` when the user asks about staged changes, and do not substitute the working-tree file for the staged file.
   - Run staged-only tests from an isolated temporary snapshot when unstaged edits exist: archive the recorded base commit, apply `git diff --cached --binary` there, run the targeted checks, and delete the temporary directory. A test run against the ordinary checkout does not verify the staged patch when `git status` shows `MM`.
   - Treat a live repository as mutable. If file contents, test counts, status, or behavior differ from an earlier read, assume the diff changed during review rather than rationalizing the mismatch. Re-read `git status`, the affected hunks, and line-numbered source before reporting findings. If a regression test appears and later disappears, do not cite the transient test as final-tree evidence; reproduce the behavior with an isolated temporary probe and cite the final production lines instead.
   - If the patch is staged or committed during review, compare tree identities (`git write-tree` for the index and `git rev-parse HEAD^{tree}` for the commit). Re-run verification against the final tree whenever the identities differ; only carry prior evidence forward when they match exactly.
   - When the user explicitly asked to verify that work stopped before commit/push and `HEAD` moves during review, report that scope condition as failed even if the final tree is clean. Record initial/final HEAD, inspect `git log`, `git reflog`, committed file scope, index/tree identity, upstream/ahead-behind state, and exact remote SHA refs when accessible. Distinguish **commit proved**, **push disproved**, and **push unknown**; lack of an upstream does not prove no push, and an inaccessible remote must be reported as unknown rather than inferred.
   - Run a final `git status --short` and the appropriate `git diff --check` range; ensure all line references and verification claims describe the final observed diff.
   - See `references/reviewing-mutable-staged-patches.md` for a copy-safe staged snapshot recipe and commit-during-review recovery.
2. Read nearby code that determines behavior, not only changed lines: event emitters, FSM/listener dispatch, task ownership, retry helpers, completion/error propagation paths, and tests/fakes that may mask real behavior.
   - When the diff touches FSM/state orchestration, re-read the source state machines and the owning executor flow from each actor's perspective before judging whether a helper or edge-case branch is necessary.
   - Trace predicate scope through downstream helpers. A correctly narrowed context can be defeated by a later route-wide/list-wide helper that scans objects outside the intended target set; use real topology or configuration-wide probes when first-fixture tests cannot expose this overlap.
   - Prefer the normal state-flow invariant over speculative defensive branches. If another state machine already owns a condition, don't duplicate that control in the reviewed code unless there is evidence the invariant can be violated.
   - When reviewing async orchestration unit tests, prefer necessary behavior seams over exhaustive edge cases: core happy path with ordering, snapshot/no-lost-wakeup, terminal fast path, pre-ready failure, post-ready cleanup failure, and one focused event-contract test.
   - A test named for a race must create actual temporal overlap. Use barriers/events to pause one coroutine at the contested boundary, start the competing callback/task, then release the barrier; sequentially awaiting operation A before invoking operation B only tests the post-A state. Assert the single-winner contract directly (transition count, cleanup count, terminal result, and loser behavior).
   - For stale-reference lock races, do not rely on `asyncio.gather()` with immediately completing mocks: one coroutine may finish before the other performs its initial read, so the test passes even if the under-lock ownership re-read is removed. Pre-acquire the production lock, start both public/source-specific entry points so each reaches the lock with the same stale reference, then release it. For command-versus-observer races, invoke the real observer handler rather than its private shared helper and assert source-aware side effects (one local transition, command-side owner synchronization, no observer callback loop).
   - For this user's code reviews, do not hide test control surfaces behind broad `patched_*_flow()` helpers. Inline grouped `patch.object(...)` blocks in each test case when they show what the scenario controls, even if this repeats boilerplate.
3. If feasible, run the smallest relevant tests to ground the review. Treat setup-only failures as environment facts, not findings.
4. Report findings as actionable review notes with file/line references, confidence, and risk. Keep test output separate from findings.
5. Honor “do not modify files” literally: no patches, formatting, generated artifacts, or cleanup commits.
6. If the user later asks to act on findings, apply only still-valid high-confidence items, re-read the live diff first, and prefer the smallest intuitive change over a new abstraction layer. For async findings, localized cancel-and-drain fixes with targeted tests are usually worth applying even when broader concurrency/API redesigns should be deferred.

## Async / Listener Safety Checklist

- Cancellation: if the parent coroutine is cancelled, are child tasks cancelled and awaited?
- Done/background tasks: if a child or fire-and-forget FSM/listener task finishes with an exception, does a done callback call `task.exception()` (or otherwise drain and propagate it), rather than merely discarding the task and leaving the public completion future pending? Probe this by injecting an exception and checking FSM state, public-task completion, completion-future state, and the loop exception handler.
- Lost wakeups: is state checked after listener registration, and is event clearing ordered safely?
- Completion-boundary races: after the last awaited authority/I/O operation, is shared state snapshotted again immediately before the success transition? Listener-first plus an initial snapshot does not catch a callback queued behind the completing task.
- Concurrent terminal events: is terminalization claimed synchronously (state/flag/lock) before awaiting cleanup, so duplicate callbacks cannot both clean up and transition?
- Confirmed-event ownership: when an entry/readiness/completion callback must await I/O, does it synchronously claim a single winner before the first await, disarm the old timer/listener, make queued timeouts consult the claim, and re-check state before the final transition? A final state guard alone does not prevent duplicate cleanup or deletion of a next-state listener. Use the true-overlap probes in `references/async-confirmation-claim-before-await.md`.
- Error-terminal propagation: if an abnormal state is lifecycle-terminal, do parent filters, fast paths, restart paths, and readiness futures still await/raise its stored failure instead of treating it like successful completion?
- Listener cleanup: are listeners removed in `finally`, including timeout/error/cancellation paths?
- Event dispatch cost: does a state transition create background tasks even when no external listener exists?
- Interface safety: does adding listener capability require every implementation/fake to remember base-class initialization?
- Persisted enums: when adding an `IntEnum` state used outside the process, append it so existing numeric values remain stable.

## Output Shape

Use concise bullets:

- `path:line-line` → problem → suggested direction | confidence | risk

Finish with `Files created/modified: none.` when no files were changed.

## References

- `references/sart-2032-async-review.md` captures one concrete async/listener review pattern that motivated this skill.
- `references/fsm-orchestration-review.md` captures the pattern for reviewing multi-FSM orchestration: re-read each actor's state flow and prefer existing state-flow invariants over speculative defensive branches.
- `references/sart-2032-mission-nibble-rereview.md` captures a concrete parent/child FSM review where removing a redundant async helper made the code cleaner and more maintainable.
- `references/async-orchestration-unit-test-review.md` captures how to simplify async orchestration unit tests without hiding the test control surface behind broad patch helpers.
- `references/async-state-ownership-review.md` captures the state-boundary lesson that ordering is not enough: place side effects in the state that semantically owns them, and test both the absence in the preceding state and the positive ordering in the owning state.
- `references/async-abnormal-terminal-races.md` covers listener-plus-final-snapshot boundaries, duplicate terminal callbacks, parent propagation of error-terminal child states, and persisted enum compatibility.
- `references/async-confirmation-claim-before-await.md` covers confirmed entry/readiness/completion callbacks that compete with queued timeouts, duplicate callbacks, next-state listener registration, and termination while awaited I/O is blocked.
- `references/reviewing-mutable-staged-patches.md` provides the copy-safe staged snapshot recipe and commit-during-review recovery.
- `references/mutable-uncommitted-diff-rereview.md` covers transient tests, isolated semantic probes, mid-review commits, final-tree re-verification, and precise commit/push-state reporting.
