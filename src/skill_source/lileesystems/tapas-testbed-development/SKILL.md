---
name: tapas-testbed-development
description: >
  Develop, modify, or review LILEE `tapas-testbed` services, Docker Compose setup,
  standalone mock containers, and uv-managed Python testbed components. Use for
  `tapas-testbed`, mock ADS, mock TriOps, testbed compose work, or Gerrit uploads
  for the testbed repo.
---

# TAPAS Testbed Development

Use this skill when working in the LILEE `tcloud/test/tapas-testbed` repo, especially when adding or changing standalone testbed containers such as mock ADS or mock TriOps.

## Required workflow

1. Load `tapas-knowledge` first for platform terms, service roles, MQTT/ICD topics, and authoritative TAPAS references.
2. Inspect the current `tapas-testbed` repo state before designing changes:
   - `docker-compose.yml`
   - `.env.example`
   - `README.md`
   - existing service directories and build conventions
3. For code changes, use a reviewable plan before large edits unless the user has already approved implementation.
4. Prefer `uv` for new Python services in this repo.
5. Before creating or resuming multi-step task state, validate `/opt/knowledge/00-system/policy-manifest.yaml`, load the effective `plan-policy.md`, and use the canonical plan location it specifies. Do not hardcode a legacy plan root.
6. Before Gerrit upload, ensure the commit subject starts with the relevant SART Jira ID.

## Testbed mock container conventions

For standalone testbed mocks:

- Put mock codebases inside the `tapas-testbed` repo and build them directly from `docker-compose.yml`.
- A `mock-ads` container represents one vehicle; add more compose services for more vehicles.
- Use `ASSET_ID` consistently for ADS vehicle IDs and TriOps asset IDs.
- Use `SAFETY_SERVER_WS_URL` for mock ADS command WebSocket configuration.
- Disable Thalos in-process mocks when standalone mock containers are enabled to avoid duplicate simulators.
- Store testbed fixture/config data that should be versioned, such as `mission_travel_time.json`, in the codebase and maintain it with git.
- Copy required Thalos const/track data into mock service codebases when independence is required; do not runtime-import Thalos if the user wants independent adjustment.

See `references/mock-ads-triops-containers.md` for the detailed mock ADS / mock TriOps decisions captured from the first standalone-container implementation.

See `references/remote-windows-compose-testing.md` for the repeatable pattern for testing this repo on the Windows AMD64 host `10.2.8.144`, including dedicated Compose project names, API probes, artifact capture, and cleanup verification.

See `references/linux-cross-repo-candidate-validation.md` for shared Linux AMD64 playground validation of coordinated Thalos/Unicorn changes. It covers isolated fresh-data Compose projects, source-built candidates, exact stock-image overlay fallback when private build dependencies are unreachable, public-API idempotency/failure probes, evidence provenance, and verified cleanup of root-owned bind data.

For standalone `plcsim` topology/wayside SSOT, load `tapas-redesign-architecture` and follow its strict sequence: human-reviewed YAML → generated JSON → generated OpenPLC ST → FastAPI/Angular Dispatch Console, with one Gerrit patch and review per item. Do not use testbed runtime concerns to broaden the YAML-only Item-1 patch. Use this testbed skill again only when an approved plcsim contract is integrated into `tapas-testbed` or exercised in Compose.

See `references/mission-driven-mock-ads-e2e.md` when a standalone mock ADS must execute a real multi-leg Thalos/Unicorn schedule. It covers effective-mission identity, refresh idempotency, exact sub-block geometry, same-block occupancy, departure/arrival FSM semantics, intermediate-platform holding, terminal-yard return, and isolated Compose evidence capture.

See `references/mock-ads-trackmap-and-controls.md` when Type 2 vehicles disappear on Crystal M1/M2/M3 or tests need independent switches for yard positioning and autonomous driving. It captures the directional `SubBlock.id` vs reported `SubBlock.name` contract, Type 13 separation, four-mode control matrix, and browser-level verification.

## Mission-driven E2E guardrails

For real mission lifecycle validation:

- Create schedules and service groups through Unicorn GraphQL/API/UI; use SQL only for read-only RCA.
- Treat source revision, local image, and running container as separate provenance layers. After pulling or checking out a patch set, explicitly rebuild and force-recreate local-build mock services before judging runtime behavior; record the source revision and do not infer it from an image tag.
- When reproducing schedule-timing behavior, match both the deployed SafeART component version and the exact departure lead time. Capture command traces relative to the mission's actual `departureTime`; yard-to-first-block positioning is driven by acceptance of an effective Type 3, not by a fixed pre-departure-minute timer.
- Treat the top-level active mission as authoritative even when the queue contains only future missions; use queue selection only before top-level activation.
- Do not reset progress for same-UUID refreshes or transient empty commands.
- At each new-mission handoff, synchronize both internal and published state: reset the public waypoint index, align the reported sub-block/milepost to the first authoritative segment, and publish route direction. Resetting only the internal path index creates protocol-visible stale geometry.
- Retire completed mission identities and keep a bounded recent-completion history through final parking. Prepared-mission expiry exceptions must not become permanent replay permission, including after `READYTOGO`.
- Derive paths from exact authoritative sub-block IDs and per-template route direction; never let a queue-stage placeholder `authorized_dir` override configured geometry. Validate continuity and eliminate legacy aliases across the entire fixture, not only the active E2E loop.
- Keep internal directional `SubBlock.id`, externally reported Type 2 `SubBlock.name`, and Type 13 physical `block_id` as separate contracts. A Crystal vehicle disappearing on selected M1/M2/M3 blocks is often a non-renderable `sub_block_id`, not an occupancy failure; verify against Unicorn mapping and actual Crystal shapes before changing IDs.
- Treat automatic yard positioning and autonomous route progression as independent, default-on controls. Gate every pre/post-departure teleport path, preserve externally patched status when auto-drive is off, and test all four switch combinations. For `position off / drive on`, use paired fresh-state checks: first verify a mission received in the yard does not teleport; separately pre-position a first-segment midpoint **before** mission receipt, verify activation preserves geometry/index, then wait for movement. For `position off / drive off`, pre-position a later valid route segment before receipt and verify path-index alignment plus zero-speed preservation. Dispatch-then-patch alone misses activation-time resets. Do not wait for a post-departure manual-position stop while still in the yard; Thalos can keep the departure signal RED and deadlock the harness.
- For frontend visibility defects, require browser-level evidence from the actual Crystal deployment. If the standard browser path is unavailable, use an isolated `/tmp` headless Playwright install, inject credentials only at runtime, capture M1/M2/M3 screenshots plus console/canvas/runtime-state metadata, and visually confirm the vehicle card; payload correctness alone is insufficient.
- Do not block transitions between sub-blocks of the same occupied physical block.
- Require Thalos mission-FSM completion at every intermediate platform, and return to parking only after the terminal yard leg. Treat a mission-less expired command as a terminal completion-clear only when the state machine is already waiting at the final platform.
- Do not call a test passed from service health, WebSocket connectivity, the first successful leg, or a transient final state; retain per-leg protocol, occupancy, mission-boundary, and stable final-state evidence.
- Start and sanity-check evidence capture before dispatch. Use the container's managed Python runner, prove destination-occupied-before-source-free from runtime records, archive artifacts before teardown, and verify cleanup separately.
- When staging the repo with tar, do not use a global `--exclude=data`: it also excludes tracked nested runtime fixtures such as `mock-ads/src/mock_ads/data/mission_travel_time.json`. Exclude only the exact root bind-data path (for example `--exclude='./data'`) and verify tracked fixture hashes/content before building mocks.
- Treat Unicorn's environment-reset API as DB-only. It does not clear service caches, PubSub state, Thalos executors/tasks, or mock ADS applied-mission state. For a definitive clean integration run, wipe the isolated bind-mounted DB before starting services (or stop/reset/restart all stateful services in the correct order); do not reset the DB after Thalos/mock ADS have loaded old state.
- Before claiming completion or uploading the final patch set, wait for any already-dispatched independent review and resolve reproduced blocking findings. A passing suite does not override a targeted state-transition reproduction.

## Verification pattern

Run service-local verification before full-stack Compose verification:

```bash
cd /opt/data/workspace/tapas-testbed

cd mock-triops
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests

cd ../mock-ads
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests

cd ..
docker compose config --quiet
docker compose build mock-triops mock-ads-1
```

Only start the full stack when registry images and environment access are known to be available.

## LILEE registry / VPN pitfall

The agent container may have VPN access that the host does not. Pulling `registry.lileesystems.com` images from the host can fail even when code is fine. If verification requires registry images:

- Try the needed pull/build from the agent/container environment first.
- Prefer targeted builds of local services when possible.
- If registry access still blocks verification, report the blocker and ask Preston to pull/provide the image rather than presenting it as a code failure.

## Gerrit upload

If the work has no Jira ticket yet, do not invent a key or create a nonconforming commit. Create the Jira issue first only when issue creation is in scope and authorized. If implementation is approved but Jira creation/publication is not, work on a feature branch, keep the reviewable tree uncommitted, record that state in `status.md`, and ask for the real Jira key before committing or uploading. Use Atlassian MCP when available, then verify the created issue before committing.

Use the repo’s Gerrit workflow:

```bash
git push origin HEAD:refs/for/master
```

If Gerrit rejects the push with `Permission denied (publickey)` because Git selected the wrong identity, do not rewrite the remote or guess credentials. Retry with the shared LILEE identity explicitly selected:

```bash
GIT_SSH_COMMAND='ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared -o IdentitiesOnly=yes' \
  git push origin HEAD:refs/for/master
```

After push, query Gerrit and verify that the new patch set points to the exact local revision and preserved `Change-Id`; do not treat a successful-looking push line as the only proof. Add the E2E/evidence summary to the Jira issue, read the comment back, and move the issue to `In Review` when the Gerrit change is ready for reviewers. Leave merge and `Done` transition to the normal review workflow unless explicitly authorized.

Commit subject format:

```text
SART-XXXX <concise imperative subject>
```

Do not invent the Jira ID. Ask the user if it is not provided.
