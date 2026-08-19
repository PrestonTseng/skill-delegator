---
name: thalos-nibble-authority-development
description: >
  Design, implement, review, or debug Thalos Nibble movement-authority behavior across ADS progress,
  WSS route/block authorization, MA range construction, recheck races, terminal handling, and Mission integration.
  Trigger for Nibble FSM changes, authority revalidation, false route rejects after block release, or ADS/WSS ordering races.
---

# Thalos Nibble Authority Development

Use this skill for behavior changes and RCAs involving Thalos `NibbleExecutor`, its FSM, movement-authority extension, WSS authorization, or Mission orchestration.

## Core Model

Always distinguish:

- **MA calculation window**: current block plus forward blocks newly covered by the proposed MA.
- **Authority target window**: forward blocks only; the current block has already been entered and its authority is being consumed.
- **Route occupancy window**: all blocks controlled by a relevant route. Do not blindly exclude the mission vehicle's current block: WSS rejects requests for routes containing an occupied controlled block. Interpret `WAIT` using the lifecycle phase and the MA already issued.
- **Facing-signal window**: the ordered signals ahead of the current Nibble. Advancing MA mileposts does not advance `facing_sig_id` / `next_facing_sig_id`; every confirmed block-entry path must update both concerns explicitly.

Do not reuse one block list or one update operation for all meanings. Read `references/forward-authority-reconciliation.md` for authority invariants and race handling. For Mission look-ahead, route-wait deadlocks, cancellation poisoning, and retry audits, read `references/mission-progression-stop-risk-audit.md`.

## Workflow

1. Inspect the live Nibble FSM, `NibbleExecutor`, Mission integration, and focused unit tests before proposing changes.
2. Reconstruct the event ordering across ADS status, WSS route/block state, route request, MA refresh, facing-signal ID update, and block exit. Distinguish domain progression from transport/reporting lag.
   - Audit the scope of every helper called after authority-context construction: a route-wide occupancy/authorization scan can silently reintroduce the current block after targets were made forward-only.
   - For an own-current-block `WAIT`, establish whether the Nibble is entering before extension MA or rechecking after current-plus-forward MA was already issued. In the latter case, ADS exit reconciliation can resolve the wait; in the former, a genuine unavailable route is a fail-safe hold and bypassing occupancy would send a request WSS is expected to reject.
   - Audit facing-signal IDs separately from MA milepost range. Verify both already-in-block snapshots and event-driven look-ahead entry callbacks; timing-dependent path coverage can make logs appear intermittent.
   - For release stop-risk audits, probe every mission and nonterminal Nibble topology, then reproduce one concrete result through the real state handler; first-block-only fixtures miss later current-block/route overlap.
3. Write focused RED tests first:
   - MA window versus authority targets;
   - current-block release versus forward-target degradation;
   - route relevance derived from forward targets;
   - own-vehicle/current-block occupancy versus route-request `WAIT`, using real mission/route topology and asserting whether forward MA was already issued;
   - facing-signal ID advancement on both already-in-block snapshot and event-driven look-ahead entry paths, including the correct ADS timestamp;
   - ADS snapshots in every post-entry phase;
   - terminal and nonterminal empty targets;
   - ADS-exit/WSS-recheck ordering and idempotency;
   - exceptional and canceled Nibble completion followed by a successful Mission retry.
4. Implement the smallest behavior change to GREEN.
5. Apply a **targeted structural refactor** after behavior is locked:
   - clarify helper names and responsibility boundaries;
   - centralize normal reconciliation and cleanup;
   - remove superseded states, exceptions, and Mission propagation;
   - preserve public contracts and major FSM phases unless a broader rewrite is explicitly approved.
6. Run focused Nibble and Mission suites after each structural change.
7. Review the final diff for reuse, correctness, and unnecessary complexity.
8. Run `./build.sh --run-tests` only after source edits stop. If files change while it runs, rerun it; stale build output is not final evidence.
9. For Gerrit, amend the existing commit, preserve its `Change-Id`, push `HEAD:refs/for/master`, and verify the resulting patch set.

## Review Standards

- Prefer domain predicates and explicit state transitions over timing sleeps.
- Do not add arbitrary ADS catch-up delays to mask an event-ordering race.
- A normal traversal/release must not become a Mission fault.
- One state handler should own normal completion cleanup and future resolution.
- Use real FSM transitions in race tests; spy/wrap them instead of replacing them with inert mocks.
- Keep changes reviewable: behavior fix first, then bounded cleanup with tests green throughout.

## Pitfalls

- Treating the current occupied block as a new authority target causes false rechecks when WSS normally releases it.
- Conversely, an own-current-block `WAIT` is not automatically a deadlock defect. If WSS forbids requesting a route containing an occupied controlled block, excluding that occupancy merely sends a request expected to be rejected. Classify the phase: after `MA_REFRESH`, current-plus-forward MA already exists and ADS exit can reconcile; before extension MA, a genuinely unavailable route is a fail-safe hold. Fix only an evidence-backed false hold, not the safety gate.
- Updating MA start/end mileposts does not update facing-signal IDs. If the snapshot entry path updates signals but the event-driven look-ahead callback only transitions state, signal IDs become timing-dependent and can remain stale after the vehicle advances.
- Once event-driven entry awaits a facing-signal MA update, synchronously claim confirmed entry before the first await. Otherwise a queued entry timeout can win during I/O, or a duplicate ADS callback can remove the listener that `ROUTE_REQUEST` just re-registered. Guard timeout commit with state plus claim, clean up old-state resources once, and keep a final state check so termination wins. See `references/pre-alpha-stop-risk-audit.md`.
- A retry transition does not repair an already exceptional or canceled completion future. Prove that retry awaits a fresh attempt signal and reaches normal completion.
- Canceling a look-ahead task that directly awaits a bare future can cancel the shared future; `CancelledError` bypasses `except Exception` and may silently abort later Mission progression.
- Treating every empty forward-target list as terminal hides configuration/range errors.
- A test that awaits `_trigger_recheck()` before sending ADS exit is sequential, not a race test. Block recheck cleanup with events, launch ADS exit while cleanup is blocked, and release cleanup only after proving the exit task is waiting on arbitration.
- When isolating exit/recheck arbitration, disable unrelated `ROUTE_REQUEST` state listeners in the test; otherwise background route-request retries can fail on irrelevant fixture settings and obscure the race contract.
- If one lock is held from the state/ADS snapshot through cleanup and the transition out of `AWAIT_BLOCK_EXIT`, a separate `_recheck_in_progress` flag is redundant: queued callbacks re-check state after acquiring the lock.
- Keep pure MA/authority range construction synchronous. Async wrappers around in-memory slicing and WSS cache reads add mock/plumbing complexity without concurrency value.
- Splitting cleanup among many branches causes duplicate listener removal and inconsistent completion timing.
- Holding onto obsolete abnormal states/exceptions after the domain decision changes leaves Mission-level fault paths alive.
- A whole-FSM rewrite in an incident patch obscures semantic changes and raises regression risk; use targeted refactoring unless explicitly approved.

## References

- `references/forward-authority-reconciliation.md` — detailed authority-window, ADS/WSS reconciliation, empty-target, concurrency, and testing rules.
- `references/mission-progression-stop-risk-audit.md` — Mission look-ahead, route-wait phase classification, cancellation poisoning, retry-safe completion futures, and pre-deployment reporting.
- `references/pre-alpha-stop-risk-audit.md` — facing-signal ownership, downstream helper-scope audits, all-topology probes, FSM listener-task hang probes, and release-gate reporting.
