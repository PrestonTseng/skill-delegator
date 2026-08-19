# Gerrit patch review reference

This reference captures a reusable workflow and heuristics from reviewing a Lilee Gerrit patch (`tcloud/safeart/unicorn` change 7910). Keep it general; do not treat any specific finding here as globally true.

## Gerrit REST calls

Gerrit JSON responses start with an XSSI prefix. Strip the first line / prefix before parsing.

```bash
# Change detail with current revision, files, labels, commit, and messages
curl -sS -L \
  'https://<host>/gerrit/changes/<urlencoded-project>~<change>/detail?o=CURRENT_REVISION&o=CURRENT_COMMIT&o=CURRENT_FILES&o=DETAILED_LABELS&o=MESSAGES' \
  | sed "1s/^)]}'//" > change-detail.json

# Patch set as base64-encoded patch
curl -sS -L \
  'https://<host>/gerrit/changes/<urlencoded-project>~<change>/revisions/<ps>/patch?download' \
  | base64 -d > change-<change>-ps<ps>.patch

# File list for a patch set
curl -sS -L \
  'https://<host>/gerrit/changes/<urlencoded-project>~<change>/revisions/<ps>/files/' \
  | sed "1s/^)]}'//" > files.json
```

For project `tcloud/safeart/unicorn`, URL-encoded project was `tcloud%2Fsafeart%2Funicorn`.

## Exact patch checkout

Gerrit patch refs follow `refs/changes/NN/CHANGE/PS`, where `NN` is the last two digits of the change number.

```bash
cd /tmp
git clone 'https://<host>/gerrit/<project>' <repo>-<change>
cd <repo>-<change>
git fetch 'https://<host>/gerrit/<project>' refs/changes/<last-two-digits>/<change>/<ps>
git checkout FETCH_HEAD
```

Example for change `7910`, patch set `1`: `refs/changes/10/7910/1`.

## Verification checklist

- Fetch Jira issue referenced by commit subject (for example `SART-1509`) before making requirement claims.
- Record Gerrit CI labels/messages, but do not treat `Verified+1` as complete semantic coverage.
- Run added-line static scan for obvious security risks.
- Run syntax checks on changed Python files when full environment is unavailable:

```bash
PYTHONPATH=src python3 -m compileall -q <changed-files>
```

- If dependencies like internal packages are unavailable, use minimal `sys.modules` stubs only to exercise repo-owned code paths. State the limitation.
- Prefer deterministic async probes for event/lifecycle behavior instead of relying only on code inspection.
- For API error-mapping patches, probe the actual handler/extension path, not just the exception class. Examples: call the FastAPI exception handler and inspect `status_code`/body; instantiate a Strawberry `SchemaExtension` via `__new__` if its constructor requires execution context, then call `resolve()` with a coroutine that raises the repo-owned `AppError` and inspect `GraphQLError.extensions["code"]`.
- For configurable timeout patches, check both the target flow and other client methods that now inherit the same timeout. A timeout added at shared HTTP-client construction can silently change unrelated route/mission/DOM flows unless their callers also map `asyncio.TimeoutError` to timeout-specific semantics.
- For polling timeout monitors, probe with the real scheduling base class where feasible. Example pattern: instantiate the monitor with fake cache/pubsub, start it with the same `timedelta` used by the registry, call the message-received method shortly after startup, and record when the stale/disconnected publish actually occurs.

## Heuristics learned

- Fan-in refactors need semantic review of the transport layer. If a pub/sub implementation stores only the latest value per topic, merging multiple source topics into one topic can drop events that were previously isolated by source topic.
- Event-driven lifecycle contracts matter. If a base class sets `RUNNING` only after `_job()` returns, then an `_job()` that waits forever in an async `TaskGroup` may leave monitoring stuck at `INIT` even while useful work happens.
- Recurring timeout monitors can miss their nominal timeout by nearly one polling interval. If timeout is 2s and polling interval is also 2s, a message arriving just after a poll may not emit STALE/DISCONNECTED until roughly 4s after the last message.
- Requirement-completeness review matters for Jira-backed patches. If a bug lists two expected behaviors and the patch implements only one, report that as a scope gap even when the implemented behavior is correct.
- When re-reviewing a revised patch, verify that a fix did not remove requirement-critical wording or structured semantics. Example: a timeout message may still include the object ID and distinct error code, but regress the required "final status unknown until refreshed" meaning.
- New tests should cover the requirement's core path, not only adjacent fallout from the implementation. If a change is for bulletin Enable-On timeout semantics, route/manual-mode timeout tests are useful but do not replace a focused `turn_on_bulletin` / `enforce_bulletin` timeout test.
- Config-default additions should be checked against test/docker-compose disable lists so new jobs do not unexpectedly start in API or integration tests.
- Moving message model classes between modules can break test imports or public import paths; search both source and tests for old import locations.

## Amending a reviewed Gerrit change when explicitly requested

Gerrit uses the `Change-Id` footer to associate amended commits with the same review. If the user explicitly asks you to fix and push the reviewed change:

```bash
# Verify you are on the exact reviewed change and preserving Change-Id
git log -1 --oneline
git log -1 --format=%B

# Stage only intentional files; do not include local tool artifacts
git status --short
git add <changed-files>
git commit --amend  # or --no-edit if the existing message remains accurate

# Push a new patch set for the same Gerrit change
git push origin HEAD:refs/for/<branch>
```

After pushing, fetch Gerrit metadata again and confirm:

- `current_revision` matches the amended local commit.
- the patch set number increased.
- the file list matches the intended scope.
- CI/build message exists or status is clearly reported as pending.

If SSH auth fails with the default key, use the profile/environment's known Gerrit SSH key/config rather than changing repo history or creating a new clone. Treat the specific key path as environment state; verify it live.

## Gerrit-ready finding format

```text
I think this patch needs one more revision before merge.

[High] <short finding title>
<explain current code behavior and evidence>. <explain why this regresses or risks the requirement>. Please <specific fix direction>.

[Medium] <short finding title>
<evidence and suggested fix>.

Please add tests for:
- <case 1>
- <case 2>
```
