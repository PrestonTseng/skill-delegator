# Mission-driven mock ADS E2E state machine

Use this reference when a standalone mock ADS must execute a real Thalos/Unicorn multi-leg schedule rather than merely maintain WebSocket/MQTT connectivity.

## Success boundary

A full-stack test is not complete when containers are healthy or a Type 3 command is received. Verify the whole lifecycle through official APIs:

1. Create the vehicle schedule/service group through Unicorn GraphQL/API or UI. SQL is diagnostic-only.
2. Observe queue-only Type 3, active Type 3, and Type 4 acknowledgements.
3. Move through authoritative block/sub-block geometry and emit Type 2 status.
4. Publish Type 13 occupancy in the correct order: occupy the new block before freeing the old block.
5. Complete every leg, dwell at intermediate platforms, transition to the next leg, and only return to yard/parking after the terminal yard leg.
6. Preserve API responses, protocol captures, state transitions, logs, and final cleanup proof.

## Command identity and refresh semantics

Thalos command payloads can change shape during a mission:

- Before activation, the effective mission may exist only in `mission_queue`.
- After activation, the top-level `mission_uuid` / `mission_static_id` are authoritative even if that mission no longer appears in `mission_queue`; do not silently select a future queued mission instead.
- A repeated Type 3 with the same mission UUID is a refresh. Update command fields without resetting path index, movement progress, departure state, or occupancy.
- A transient Type 3 with no effective mission must not clear an in-progress mission. Preserve the active mission until the path actually completes.
- A prepared or already-active mission may legitimately continue after its scheduled end time when the stack is delayed. Reject a brand-new stale command, but do not halt an accepted mission solely because the schedule window elapsed.
- A prepared identity must not remain an expiry exemption forever. When a mission completes, retire it and reject later replay even if it was once queued. Keep a bounded recent-completion history across final parking so a delayed old command cannot restart the finished service; mission UUIDs are unique, so new services should use new UUIDs.
- While a mission is active and not complete, reject a different requested mission rather than switching movement state prematurely. Activate a different mission only from the completed-platform handoff state after validating that its first physical block matches the current platform.
- At activation, reset both internal and published progress. Set the public waypoint index to `0`, total path size to the new path, reported sub-block/milepost to the new path's first authoritative segment, and reported direction from route metadata. Resetting only an internal index leaves Type 2 status describing the previous leg while movement executes the next leg.
- After the terminal platform has completed, a mission-less command can be the completion-clear handshake that releases the final mission and returns the vehicle to parking. Accept an expired clear only when the state machine is already waiting for terminal completion; do not weaken the general stale-command rejection rule.
- Once parked, idle mission-less commands must preserve `READYTOGO`/parking state. Do not force a generic `AUTHORIZED` state when no mission is being applied.
- Log effective-mission identity changes during RCA. UUID oscillation is otherwise difficult to distinguish from signal or geometry stalls.
- Keep command-selection and Type 4 acknowledgement traces bounded (for example, a fixed-size deque) and expose them through debug endpoints. Record enough identity, queue, direction, signal, and ACK status to reconstruct why a command was selected or rejected without retaining unbounded payload history. ACK evidence should distinguish the incoming command mission identity from the mission that remained/applied in vehicle state; using only the current vehicle mission mislabels rejected stale commands.

## Geometry, direction, and occupancy

Build mission paths from authoritative Thalos mission and sub-block constants, not block-name heuristics or queue-stage command placeholders.

- Treat route direction as mission-template metadata. A queue-only Type 3 may carry a placeholder `authorized_dir`; if it overrides route direction, the first segment can be reversed or skipped when the previous leg ends on the same physical block.
- Keep exact sub-block IDs such as `_L`, `_R`, and numbered segments. Collapsing them into one block alias can move the simulated vehicle past the platform or create discontinuities.
- Validate the complete versioned travel-time fixture, not only the loop under test: reject legacy physical-block aliases and assert every configured route is continuous after direction normalization. This prevents an E2E-specific fix from leaving sibling routes geometrically invalid.
- When an authoritative Thalos route splits a former alias into multiple sub-blocks, preserve its total travel time by partitioning the old segment time across the replacements, then test that the route total remains unchanged.
- Assert every required leg has a continuous path: each segment's end milepost equals the next segment's start milepost after direction normalization.
- Milepost units are 10 cm unless the current ICD says otherwise; convert authorized speed from km/h to m/s.
- For decreasing movement, reverse each segment's start/end orientation.
- Transitions between two sub-blocks of the same physical block must not query block-level occupancy as if entering another train's block. Update only the sub-block/milepost and keep the block occupied by the same vehicle.
- For a real block transition, occupy the destination first, then free the source.

## Departure, arrival, and multi-leg behavior

- Treat departure/facing signal authorization as a departure gate. Once the vehicle has demonstrably moved for that leg, a subsequent reset to RED must not re-arm the departure gate.
- Do not mark a vehicle as departed merely because it was teleported from parking to the first service-line sub-block; mark it after actual milepost movement.
- At a destination platform, report zero speed and the parked-on-platform vehicle status expected by Thalos (`ATO_PARKED_ON_PLATFORM` in the current ICD) so the mission FSM can leave `ARRIVING` and finalize.
- Preserve that parked status across same-mission Type 3 refreshes.
- After an intermediate mission, remain at the destination block/sub-block while a subsequent service is activated. A brief empty queue between services is not a request to return to yard.
- Return to configured parking and `READYTOGO` only after the terminal yard/platform leg has completed and the active mission clears.

## Mission-template pitfall

Mission static IDs with the same endpoints can have multiple route variants. Before dispatching a long loop:

1. Verify the requested variant exists in the deployed Thalos version.
2. Reject templates whose authoritative elapsed-time list contains sentinel/negative values.
3. Select an existing valid variant that preserves the requested endpoints, and record the variant substitution in the evidence.

Do not manufacture unsupported mission IDs in the test fixture.

## Regression-test matrix

Add concise tests for each state transition before restarting the full stack:

- queue-only mission selection;
- top-level active mission winning over future queued missions;
- same-UUID refresh idempotency;
- transient empty command preserving active progress;
- delayed accepted mission continuing after schedule expiry;
- completed prepared mission replay rejected during a later active mission and after final parking;
- mission handoff resetting published waypoint index and aligning first sub-block, milepost, and route direction;
- a different mission request rejected while the current mission is still moving;
- expired terminal completion-clear accepted only after final platform completion;
- configured route direction overriding a queue command's placeholder direction;
- all versioned travel-time routes using authoritative sub-block IDs, preserving route totals, and remaining continuous;
- same-block sub-block transition without self-occupancy blocking;
- departure signal reset after movement;
- parked-on-platform status preserved during arrival refreshes;
- intermediate-platform hold versus final-yard return;
- idle mission-less commands preserving stable `READYTOGO` after parking;
- ACK traces preserving both command and applied mission identities;
- destination occupancy published before source release on real-block transitions.

## Evidence-capture reliability

A long E2E should fail early if its evidence pipeline is not producing data:

1. Start MQTT, state, command-selection, and ACK capture before GraphQL dispatch.
2. Run helper scripts through the image's managed environment (`uv run python ...` for uv-built containers) rather than assuming a bare `python` executable is on the runtime PATH.
3. Within the first movement interval, verify each expected artifact exists and its line count is increasing. Fix capture before spending another full route duration.
4. Decode Type 2 and Type 13 records into reviewable JSONL; count messages by topic/type, mission ID, vehicle status, and occupancy wire value.
5. Prove destination-before-source occupancy ordering from captured transitions, not just from implementation order.
6. Capture final command trace, ACK trace, state, GraphQL responses, and Compose logs before teardown. Require final success to remain true for several consecutive polling samples (for example, 10 × 500 ms) so a one-frame `READYTOGO` cannot hide immediate drift back to `AUTHORIZED`.
7. At the first observation of every new mission, assert the expected authoritative first sub-block, public waypoint index `0`, and route direction. Save these boundary checks and make any mismatch fail the run.
8. Stop live capture writers before creating the archive; otherwise `tar` can fail with `file changed as we read it` or produce an inconsistent artifact. Package remote artifacts as one tar archive before transfer.
9. Verify the archive locally, write a concise evidence README, then tear down and separately record that no project-labelled containers, networks, or volumes remain. Helper containers launched with `docker run` may share the Compose project label but survive `docker compose down`; remove and recount them explicitly.

## Local-build provenance and manual-departure RCA

Pulling or checking out a Gerrit patch set updates source only; it does **not** update an already-built local Compose image or an existing container. Before comparing behavior across patch sets or runtime versions:

1. Record the source revision with `git rev-parse HEAD`.
2. Rebuild and recreate the local mock explicitly, for example:
   `docker compose up -d --build --force-recreate mock-ads-1`.
3. Do not treat an image tag such as `latest` as proof that the container contains the checked-out source.
4. Repeat the exact reported scenario against the intended Thalos/Unicorn/Crystal version and schedule lead time; a passing 20-second dispatch does not prove a 60-second manual dispatch.
5. Capture `/debug/state`, `/debug/command-trace`, and `/debug/command-acks` from dispatch through departure.

For a vehicle that does not leave yard or appear on `AV-1T`, classify the failure before changing code:

- **No effective mission in the trace:** inspect the Type 3 queue/top-level payload and upstream scheduling.
- **Mission selected but no path:** verify the exact mission static ID exists in the versioned travel-time fixture; an empty path defers fallback positioning until the normal departure gate.
- **Mission/path selected but status remains in yard:** inspect command ACKs, WebSocket connectivity, target asset ID, and motion-loop events.
- **Checked-out fix is absent at runtime:** rebuild/recreate the local mock image and rerun before opening a code defect.

Measure positioning relative to the mission's actual `departureTime`. Queue-only mission selection should place the mock on the route's first authoritative sub-block as soon as that effective Type 3 is accepted, then hold at zero speed until departure time and signal authorization. This is command-driven, not a hard-coded “N minutes before departure” timer.

## Isolated Compose execution

Use a unique Compose project and clean bind-mounted data, not just named volumes. A repeatable run should:

- `docker compose -p <project> down -v --remove-orphans`;
- remove/reset project-specific DB and service-log directories with appropriate container permissions;
- rebuild local mocks from the exact working tree;
- run DB migration and wait for health checks;
- start protocol/state capture before dispatch;
- run the schedule through GraphQL/API;
- retain failed-run artifacts under diagnostic names instead of overwriting them;
- on success, capture final state and then prove cleanup.

A failed E2E that reveals a new state-machine defect should produce a focused regression test before the next clean run.