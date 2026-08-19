---
name: gerrit-code-review
description: Review Gerrit changes and patch sets with source-of-truth requirement grounding, local checkout, targeted verification, and Gerrit-ready findings.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [gerrit, code-review, jira, patch-review, verification]
    related_skills: [requesting-code-review, systematic-debugging, tapas-knowledge]
---

# Gerrit Code Review

Use this when the user asks to review a Gerrit change, patch set, or Lilee Gerrit URL such as `/gerrit/c/<project>/+/CHANGE/PS`.

This skill is for **reviewing someone else's patch** by default. Do not push, amend, vote, or comment in Gerrit unless the user explicitly asks.

When the user explicitly asks to update or push a Gerrit change for Lilee/unicorn-style repos:
- First provide a reviewable plan and wait for explicit approval before editing code.
- Preserve the existing `Change-Id` by using `git commit --amend` for follow-up patch sets.
- Push to review with `git push origin HEAD:refs/for/master`.
- For repository SSH operations, prefer the shared key directory `/opt/data/shared/ssh`; a known Gerrit key pattern is `GIT_SSH_COMMAND='ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared -o IdentitiesOnly=yes' git push origin HEAD:refs/for/master`.
- Do not assume Gerrit accepts the generic SSH username `git` when cloning a related private project or querying Gerrit. Derive the authenticated `user@host` from a trusted working `origin` URL, substitute only the project path, and avoid printing the credential-bearing remote. This preserves the verified identity while keeping secrets out of logs.
- Before committing, verify the repo has a usable `user.name` / `user.email`. If missing, derive the identity from trusted repo/Gerrit context such as the remote username or recent commits; use `git -c user.name=... -c user.email=... commit ...` for a repo-local one-off rather than changing global config.
- In Git worktrees, the worktree-specific gitdir may not have Gerrit's `commit-msg` hook even when the main checkout has it. Before committing, check `test -x $(git rev-parse --git-dir)/hooks/commit-msg`; if missing and the main repo has `.git/hooks/commit-msg`, create `$(git rev-parse --git-dir)/hooks/` and copy the hook there so the commit gets a `Change-Id`.
- Before the first review push, inspect `git show -s --format=%B HEAD` and require a valid `Change-Id: I<40 hex>` trailer. If it is absent, bootstrap Gerrit's hook and run `git commit --amend --no-edit`; then re-check the clean tree and `git diff HEAD^..HEAD --check` before pushing. To bootstrap, prefer the Gerrit HTTPS endpoint `https://<host>/<gerrit-context>/tools/hooks/commit-msg` (some servers close the SCP hook endpoint): download to a temporary path, require a non-empty script whose first line is a shebang, then install it mode `0755` into `$(git rev-parse --git-dir)/hooks/commit-msg`. The standard SCP `-p 29418 <user>@<host>:hooks/commit-msg` remains a fallback when enabled.
- After `git push origin HEAD:refs/for/<branch>`, do not rely only on the push banner. Query Gerrit by the returned change number and read back project, target branch, status, current patch-set number, revision SHA, and ref; confirm the revision equals local `HEAD` before reporting success.
- If the user says to stop implementation and push the current checkpoint, freeze scope immediately, remove only clearly identified unfinished follow-up edits/RED tests, rerun fresh gates, publish the coherent checkpoint, and do not automatically create another patch set when a late async review returns. See `references/checkpoint-push-after-stop.md`.
- Treat project verification commands as repository-specific: inspect `build.sh --help` / project docs before adding flags. For thalos, `./build.sh --run-tests` is the CI-like path and `build.sh` does **not** accept `--ssh-key`; use `GIT_SSH_COMMAND` only around git/SSH operations.
- For Unicorn repos using uv and private Gerrit dependencies, local focused/full pytest may require `PYTHONPATH=src` plus `GIT_SSH_COMMAND='ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared -o IdentitiesOnly=yes -l <gerrit-user>'` during dependency sync.
- Report the Gerrit change URL and whether the push created a new change or updated an existing one.

## Core principles

- Review the **exact patch set**, not the branch tip or a guessed local diff.
- Ground requirement claims in the source of truth: Gerrit metadata/change description and linked Jira/Confluence when referenced.
- Prefer targeted, executable verification over plausibility-based review.
- Report findings by severity with concise Gerrit-ready wording.
- Keep task records in `/opt/data/plans/YYYY-MM-DD-<task-slug>/status.md` for non-trivial reviews unless the user requires a no-file-modification/read-only review.

## Workflow

1. **Create / update a task record unless the review must be read-only**
   - Use `/opt/data/plans/YYYY-MM-DD-review-<repo>-<change>/status.md`.
   - Record Gerrit URL, change number, patch set, scope, verification commands, and conclusions.
   - If the user says not to modify or create files, treat that as applying to review artifacts too: do not create the task record, virtualenv, generated reports, or bytecode in the checkout. Keep notes in-session and verify the final worktree is clean.

2. **Fetch Gerrit metadata**
   - Use Gerrit REST endpoints for detail, current revision, files, labels, and messages.
   - Strip Gerrit's XSSI prefix `)]}'` before parsing JSON.
   - Capture CI verification state, review status, owner, subject, insertions/deletions, and changed files.
   - If the user adds a related Gerrit link, treat the changes as one review unit unless told otherwise. Record each exact patch-set revision and inspect cross-repository field names, units, defaults, serialization, state-transition ordering, rollout dependency, and consumer visibility. A green build in each repository does not prove the combined contract works.

3. **Read the requirement source**
   - If the subject or commit message references Jira (for example `SART-1509`), fetch the Jira issue directly through Atlassian MCP.
   - Review against the stated requirement, not just against the implementation's apparent intent.
   - Resolve source hierarchy explicitly when several artifacts disagree. A live authoritative behavioral spec outranks an assignee-authored implementation plan or patch-set rationale unless the owning team has formally accepted the deviation. Do not let “preserve the existing contract” silently weaken a required operator workflow.
   - For changes with several patch sets, compare the current patch set with the immediately preceding meaningful patch set, not only with the target branch. Removed response models, tests, or transport fields can reveal a contract regression that the final branch diff obscures.
   - When the newer patch set changes only tests, distinguish a production behavior regression from an evidence regression and from a pre-existing coverage gap. Read deleted tests from the previous revision, inventory surviving coverage by layer (schema text, service, resolver/handler execution, real dependency, consumer contract), and verify whether an environment-gated cross-repository test was actually runnable. For breaking GraphQL renames, validate real consumer operations against the exact producer schema and pin the consumer revision in the finding; see `references/patch-set-test-deletion-review.md`.
   - When Gerrit labels the current revision `TRIVIAL_REBASE`, verify that the previous and current revisions have the same stable patch ID before carrying earlier review conclusions forward. Fetch both exact patch refs and compare `git show <rev> --pretty=format: | git patch-id --stable`; matching IDs confirm the content patch is unchanged even though the parent and commit SHA moved.

4. **Fetch the exact patch set locally**
   - Clone/fetch the Gerrit project under `/tmp`.
   - Use a unique checkout path containing the worker identity, repository, change, and patch set (for example `/tmp/leo-crystal-7990-ps1`). When parallel sub-agents inspect the same change, assign each a distinct path explicitly; a predictable shared path can let one worker move another worker's HEAD or remove its dependencies, invalidating verification evidence.
   - Fetch the patch ref: `refs/changes/NN/CHANGE/PS`, where `NN` is the last two digits of the change number.
   - Check out `FETCH_HEAD` so all file reads and tests use the exact reviewed patch set.
   - Immediately before verification and again before reporting, confirm `git rev-parse HEAD` matches the pinned revision and the checkout is clean. If either check fails, discard results from that checkout and repeat verification in a fresh isolated path.

5. **Inspect changed code and surrounding contracts**
   - Read the patch and the changed files.
   - Also read adjacent abstractions, base classes, pub/sub semantics, lifecycle managers, tests, and config defaults that determine runtime behavior.

6. **Run feasible verification**
   - Run static added-line security scan for secrets, shell injection, eval/exec, unsafe deserialization, and SQL string formatting.
   - Run syntax checks or project tests when dependencies are available.
   - For read-only Python reviews without a project environment, prefer an isolated, no-project runner that keeps dependency setup out of the checkout, for example: `PYTHONPATH=src uv run --isolated --no-project --python <version> --with '<minimal-dependency>' pytest --confcutdir=<focused-test-dir> <test-path>`. Use `--confcutdir` only when the focused test is intentionally independent of repository-wide fixtures; report that limitation. Do not use `compileall` in strict read-only reviews because it may create ignored `__pycache__` files.
   - If full dependencies are unavailable, use minimal stubs only to exercise repo-owned behavior. State that limitation clearly.
   - Prefer small deterministic reproduction scripts that demonstrate the exact behavior being reviewed.
   - For timeout, freshness, disconnected-state, or recurring-job patches, verify the *observed end-to-end timing*, not just the predicate/helper function. A timeout checked by a polling recurring job may emit stale/disconnected state up to one polling interval later than the configured timeout.
- For linked changes across repositories, review the complete producer-to-consumer contract and compare prior patch sets when the current revision removes response fields or tests. See `references/cross-repository-contract-review.md`.
- For GraphQL field/argument/input/enum removals, clone and pin the current consumer source, extract and validate its real operations against the producer's production schema, distinguish failures newly introduced by the reviewed patch from failures inherited from its parent, and treat deletion of a real consumer contract test as coverage regression. Require a compatibility alias or an explicit paired consumer change with verified atomic release ordering. See `references/graphql-consumer-contract-review.md`.
- For static TrackMap Line / Track / Lane semantic patches, inventory every competing identity field across blocks, signals, serializers, and active validators; then prove that configured values belong to the field's declared domain. Compare prior patch sets when canonical hierarchy/display definitions or fail-fast validation disappear, and reconcile design-page claims that no longer match the code. Keep canonical IDs separate from display labels. For bulletin endpoints, distinguish public “signal or milepost” input from downstream resolved representations, trace precedence when both are supplied, validate endpoint pairs rather than only individual fields, and test whether scalar interval merging matches physical connectivity. See `references/static-track-map-semantic-review.md` and `references/bulletin-location-semantic-review.md`.
- For PubSub / subscription patches, review both directions of semantic drift: latest-value/coalescing can drop required operation events, while queue-all changes can regress latest-state/high-frequency topics with stale backlog or unbounded queues. Inventory all affected topics, not only the Jira-mentioned topic. When reviewers ask for explicit semantics, prefer required `delivery_mode` at call sites over hidden policy maps, and run an AST sweep for subscribe calls missing delivery mode. For immutable snapshot claims, verify publisher, fanout, replay, and subscriber-boundary isolation; a single publish-time copy may not prevent one consumer's mutation from leaking to another subscriber or future LATEST replay. If the accepted optimization is instead a **shared read-only snapshot**, document that rule on the public `subscribe` API—not only in an implementation comment—before removing mutation-isolation tests. Keep a separate publisher-mutation test, and make the fanout test return a distinct publish snapshot so it can assert both one-copy count and object identity across subscribers. See `references/sqlalchemy-pubsub-review.md`, `references/pubsub-gerrit-followup-review.md`, and `references/pubsub-immutable-snapshot-review.md`.
- For diagnostic instrumentation patches (stack samplers, profilers, tracing, verbose logs, incident capture), review the diagnostic path as production code: check output size, event-loop/hot-path impact, queue bounds, and whether repeated warnings can flood logs or amplify the incident. See `references/diagnostic-instrumentation-review.md`.
- For diagnostic-removal patches after an RCA narrows its evidence protocol, do not assume removed observability is a regression. Read the current Jira/Confluence RCA source, confirm whether the diagnostic is superseded/disabled/out of scope, then sweep for stale symbols and run the CI-like path. See `references/thalos-rca-diagnostics-removal-review.md`.
- For frontend rendering/performance patches that suppress duplicate work or defer DOM/canvas/Konva updates through `Image.onload`, `requestAnimationFrame`, timers, observers, or promises, test async ordering explicitly: issue state B, then newer state C before B's async callback completes, then flush callbacks and assert only C remains. See `references/frontend-async-rendering-review.md`.
- For state-machine changes that recalculate an external command after lifecycle events, test the listener-handoff window explicitly: block the command send after calculating old state, emit the newer lifecycle state with production-faithful scheduling, release the send, and assert the eventual final command reflects the newer state. Confirm the listener is actually registered in the exercised state; manually awaiting callbacks can hide races when production uses `asyncio.create_task`. Also test inverse/removal transitions independently (for example, `EFFECTIVE -> EXPIRED` must restore authority, not only `SCHEDULED -> EFFECTIVE` restrict it). For Thalos Bulletin/MA details, see `references/thalos-bulletin-async-ordering-tests.md`.
- For UI/E2E tests that claim to validate visual placement or rendering, distinguish behavioral/geometric oracles from self-reported DOM metadata. Attributes added by the patch and bound directly from the same view model under test can prove propagation, but cannot prove that the element is rendered at the correct coordinates, on the correct geometry, or through the correct visual path. Preserve an independent oracle (for example, track geometry, hit-testing, screenshot comparison, or an independently computed expected transform) and treat metadata assertions as supplementary diagnostics.
- For Angular/Nx frontend patches, run layered verification: focused changed-area tests, build, lint, and full project tests when feasible. When passing multiple files through Nx/Jest, verify that the reported suite count matches the requested file count: some `nx test ... --runTestsByPath <file1> <file2> ...` invocations may silently execute only one path. If counts do not match, run Jest directly with the project config or execute each focused path separately; never summarize the requested list as tested based only on exit code. For refactors that extract helpers, add a focused unused-export check (for example `ts-prune` scoped to changed paths) so module-internal types/functions are not accidentally exposed as public API. For Apollo GraphQL changes, review default HTTP client vs named websocket client usage, and check whether service tests cover the actual GraphQL documents rather than only component mocks. See `references/frontend-angular-gerrit-review.md` and `references/angular-nx-focused-verification.md`.
- For Crystal / Angular E2E patches that seed synthetic records or introduce E2E-only modes, check that the seeded record is valid across all production UI rendering paths, not only the test's main path. In particular, a non-user-defined seeded mode needs matching i18n entries for every key family the UI uses; do not let tests assert raw fallback keys such as `can.someMode`. See `references/crystal-e2e-mode-review.md`.
- If local SSH clone/fetch is blocked but Gerrit REST and HTTPS Git access are reachable, use the exact-patch fallback: fetch change metadata and the base parent over HTTPS, download the revision patch from the REST `.../patch?download` endpoint, base64-decode it, apply it in a temporary detached worktree, and run `git diff --check` plus targeted inspection there. This preserves exact patch-set review without changing the user's checkout. If only REST is reachable, use the REST-only fallback to fetch change detail, patch, comments, and exact file contents. Clearly label that full local tests were not run and do not overclaim verification. See `references/gerrit-rest-only-review-fallback.md`.
- For Thalos MissionExecutor/NibbleExecutor departure-flow comments, prefer a simple linear event/future-based departing orchestration over broad abstractions unless the broader abstraction is clearly reused. See `references/thalos-departing-event-review.md`.
- For Thalos startup bulletin max-speed revalidation, map product terms to persisted states explicitly (`DISABLED`, `SCHEDULED`, `EFFECTIVE`; exclude `EXPIRED`), verify warning-only behavior through `BulletinService.start()`, and assert no state mutation, persisted bulletin-log entry, or consumer notification. Compare revised Jira requirements against obsolete patch-set descriptions before judging notification scope. See `references/thalos-startup-bulletin-revalidation-review.md`.
- For Thalos bulletin lifecycle patches that affect movement authority, test both directions of state drift: `SCHEDULED -> EFFECTIVE` must restrict active MAs, while `EFFECTIVE -> EXPIRED/DISABLED` must remove restrictions. Inventory listener gaps across `ROUTE_REQUEST`, `MA_REFRESH`, and `AWAIT_BLOCK_EXIT`; demonstrate the final range sent by `set_range()`, not only helper output. A relevance predicate must accept removal events such as `EXPIRED`, and directly awaiting callbacks can hide the production emitter's `asyncio.create_task()` scheduling. A `SCHEDULED` test with `start_time=None` is a false oracle for the future-start race when that combination is already treated as directly effective; require a non-null future start time and assert the listener was actually armed. Also compare the event-relevance domain with the MA-calculation domain: if MA calculation includes the current block plus forward blocks, a forward-only route context is too narrow. Run separate current-block-only activation and removal probes and assert both the lifecycle revision and eventual final range. See `references/thalos-bulletin-async-ordering-tests.md`, `references/thalos-bulletin-lifecycle-race-review.md`, and `references/thalos-bulletin-ma-refresh-race-review.md`.

7. **Map patch scope back to the source requirement**
   - If the Jira/Confluence requirement has multiple expected behaviors, check each one explicitly.
   - A patch may be valid but still only partial; report missing requirement bullets as scope gaps rather than assuming the Gerrit subject fully captures the issue.

8. **Write findings**
   - Use severity labels: High / Medium / Low / Minor.
   - For each finding include: affected file/behavior, why it matters, evidence from code or command output, and suggested fix direction.
   - When the user asks for only high-confidence actionable findings, omit review narrative, non-findings, speculative concerns, and paste-ready comment prose. Include verification commands/results only as evidence for reported findings or in one compact verification footer if explicitly requested.
   - Include a short paste-ready Gerrit comment when useful and not excluded by the requested output format.
   - When the user asks for a clearer explanation, do not merely restate the verdict. Name the exact patch set/revision, show the old-vs-new data flow, give one concrete false-pass or failure example, state the runtime/user impact, and say exactly what must change or what the follow-up fixed. In Discord, prefer short headings, bullets, and compact code-flow blocks over tables.
   - For follow-up patch sets, report the prior finding as `fixed`, `partially fixed`, `still present`, or `obsolete`, then separate any newly introduced findings. State build/lint/unit/discovery/full-E2E evidence independently so Playwright discovery or Gerrit `Verified+1` is never presented as an executed integrated scenario.

9. **If explicitly asked to handle Gerrit comments, amend, and push the reviewed change**
   - Fetch Gerrit inline comments/messages from the source of truth first (for example `/changes/<change>/comments`, with the XSSI prefix stripped), even if the user summarized the comment in chat.
   - Read every Gerrit inline comment/message and classify each one as blocking, accepted suggestion, rejected-with-reason, or needs-question before editing.
   - Confirm the local checkout is the intended Gerrit change/patch set and that the commit message contains the existing `Change-Id`.
   - Make the smallest targeted fix; avoid committing unrelated untracked files or local tool artifacts.
   - When a review comment changes a configuration contract, update the matching `.env.example` and README guidance in the same patch so rendered config and docs cannot drift.
   - For protocol enum/value comments, ground the correction in the current source-of-truth ICD or specification, then add a test that verifies the encoded wire payload rather than only the in-memory enum.
   - Run a separate self-review on the revised diff, not only the reviewer-comment lines. Check for semantic drift, hidden defaults, and call-site contracts affected by the fix.
   - Re-run targeted tests/static checks that cover both the original review issue and the follow-up change. For compose changes, render with the documented env file and assert both removed variables and required literal values in the rendered configuration.
   - Amend the existing commit, preserving the `Change-Id` so Gerrit creates a new patch set instead of a new change.
   - Push with `git push origin HEAD:refs/for/<branch>`.
   - Do not manually mark Gerrit comments resolved unless the user explicitly asks; updating the patch set is usually enough for the reviewer to verify.
   - Read Gerrit metadata back and report the new patch set number, revision SHA, and CI/build status link if present.

## Pitfalls

- Do not assume CI `Verified+1` means runtime semantics are correct; CI may not cover new paths.
- Do not review only the added file. New fan-in, lifecycle, config, or pub/sub changes often regress behavior through surrounding infrastructure.
- Do not harden missing local dependencies into a durable conclusion. If dependency setup blocks full tests, run targeted probes and label the coverage limit.
- Do not use GitHub PR tooling for Gerrit reviews.
- Do not vote or publish comments unless explicitly requested.

## References

- `references/patch-set-test-deletion-review.md` — review method for test-only patch-set deltas: behavior vs evidence regression, coverage-layer inventory, consumer GraphQL probes, stale-gate checks, and revision-scoped reporting.
- `references/checkpoint-push-after-stop.md` — freeze-scope, rollback-to-coherent-checkpoint, fresh-gate, Gerrit readback, and late-async-review reconciliation procedure after a user-directed stop.
- `references/schema-centric-change-review.md` — composed-model review for multi-document engineering schemas: cross-reference semantics, topology/turnout traversal, resource-release ownership, catalog capabilities, negative probes, and late async review after push.
- `references/gerrit-change-id-bootstrap.md` — first-push preflight, safe `commit-msg` hook installation via local copy/HTTPS/SCP, metadata-only amend verification, and post-push Gerrit read-back.
- `references/cross-repository-contract-review.md` — joint-review checklist for linked Gerrit changes: source hierarchy, patch-set regression comparison, producer-to-UI contract tracing, pre-confirmation mutation ordering, and cross-repository verification.
- `references/graphql-consumer-contract-review.md` — deterministic producer/consumer GraphQL review: pin live consumer source, validate real operations against the production schema, isolate patch-specific failures, detect deleted contract gates, and require compatibility or atomic rollout evidence.
- `references/static-track-map-semantic-review.md` — checks for Line/Track/Lane domain contradictions, stale identity fields, removed canonical hierarchy, cross-repository ownership parity, and design/code drift.
- `references/bulletin-location-semantic-review.md` — checks for identity/display conflation, conflicting signal/manual endpoints, pairwise direction/range validation, interval-connectivity assumptions, ownership invariants, and read-only isolated probes.
- `references/gerrit-patch-review.md` — concrete REST/fetch commands, verification checklist, and lessons from a SafeART/unicorn Gerrit patch review.
- `references/sqlalchemy-pubsub-review.md` — review heuristics and deterministic probes for DB-change listeners, SQLAlchemy `session.info` rollback cleanup, and latest-value PubSub vs operation-specific event semantics.
- `references/diagnostic-instrumentation-review.md` — review heuristics for stack samplers, profilers, tracing, verbose logs, and other diagnostics that may perturb the incident they are meant to observe.
- `references/thalos-rca-diagnostics-removal-review.md` — thalos/SART RCA diagnostic-removal review notes: source-of-truth calibration, stale-symbol sweeps, and CI-like verification for patches that remove temporary observability.
- `references/frontend-async-rendering-review.md` — review heuristics and deterministic probes for UI rendering optimizations with async image/frame/timer/observer callbacks and pending-state suppression.
- `references/thalos-bulletin-async-ordering-tests.md` — coverage matrix and deterministic race-test guidance for Nibble MA recalculation across scheduled, effective, and expired Bulletin transitions, including production-faithful `create_task` listener ordering.
- `references/thalos-nibble-fsm-gerrit.md` — thalos-specific notes for nibble FSM route authority work: build verification, Gerrit SSH usage, commit identity, owner-aware route checks, occupied-block revoke/request rules, and event-driven WSS/ABS/bulletin rechecks.
- `references/thalos-departing-event-review.md` — thalos departing-state review notes: Gerrit comments workflow, event/future-based departure readiness, signal reset timing, cancellation ownership, and focused verification commands.
- `references/thalos-bulletin-overlap-review.md` — thalos-specific review notes for bulletin milepost overlap patches: uv dependency setup, CI-like verification, normalized range edge cases, and lint interpretation.
- `references/pubsub-gerrit-followup-review.md` — PubSub Gerrit follow-up notes: explicit delivery-mode call sites, AST sweeps, TTL clock-source review, immutable payload boundary, close signaling, and verification checklist.
- `references/pubsub-immutable-snapshot-review.md` — deterministic probes for checking subscriber-side mutation leakage across LATEST replay and ALL fanout when a patch claims immutable snapshot semantics.
- `references/crystal-e2e-mode-review.md` — Crystal / Angular E2E fixture review notes: recorded-data placement oracles, seeded system modes, i18n coverage, fixture integrity, raw transloco-key assertions, and setup-project verification.
- `references/tapas-testbed-mock-followup.md` — TAPAS mock review follow-up: Type 13 occupancy wire values, direct-compose configuration review, and Windows amd64 validation.
