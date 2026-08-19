# Thalos nibble FSM / Gerrit implementation notes

Session-derived notes from implementing SART-1848 in `tcloud/safeart/thalos`. Use these as a concrete example when future Gerrit implementation work touches thalos nibble execution, WSS status handling, or route authority checks.

## Repository verification

- Pull latest master before coding: `git pull --ff-only origin master`.
- The thalos project verification command is:

```bash
./build.sh --run-tests
```

- `build.sh` supports `--run-tests` and optional registry/version arguments; it does **not** accept `--ssh-key`.
- Use shared SSH key configuration only for git/Gerrit operations, e.g.:

```bash
GIT_SSH_COMMAND='ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared -o IdentitiesOnly=yes' \
  git push origin HEAD:refs/for/master
```

## Commit identity pitfall

Fresh containers may lack `user.name` / `user.email`. Do not set global config casually. Prefer a one-off commit identity derived from trusted Gerrit/repo context:

```bash
git -c user.name='Preston Tseng' \
    -c user.email='preston.tseng@lileesystems.com' \
    commit -m 'SART-1848 Refactor nibble FSM authorization flow'
```

Adjust identity to the actual requested owner/user for the task.

## Nibble FSM authority lessons

For nibble executor route authority changes, avoid the old bug pattern of checking only `route_state == AUTHORIZED`. The validation needs to consider:

- route state,
- route owner,
- route-controlled block authorization,
- block occupancy,
- ABS direction state only when the PLC/source is trusted,
- signal/bulletin changes that can invalidate a previously valid authority snapshot.

If PLC ABS Direction logic is known to be faulty, temporarily keep ABS Direction out of `NibbleExecutor` entirely: remove ABS Direction from authority evaluation and do not register ABS Direction recheck/wakeup listeners. It is OK for `WSSAgent` to keep ABS Direction cache/event support as a service-layer capability; the nibble executor should simply ignore it until the PLC source is fixed.

When route/block state is inconsistent, revoke+request is only appropriate if there is no unrelated occupied controlled block. If an unrelated controlled block is occupied, a route request is expected to fail; keep waiting for state changes instead. If the occupied block is the current vehicle's own block, treat that as normal occupancy, not an intrusion.

For block-exit completion, this session's user correction was explicit: completion should check `status.block_id != self._block.id`; do not also require sub-block inequality. Do **not** over-apply this to block-entry detection: entry can still accept either `status.block_id == block.id` or `status.sub_block_id == block.id` so a vehicle already reported in the target sub-block is not missed.

For terminal/final-station nibbles, do not wait for block exit: the vehicle may stop at the terminal station and end the mission while still occupying the terminal block. Add an `_is_terminal_nibble()` helper (`self._block.id == self._mission.block_id_list[-1]`) and complete the nibble immediately when it enters `AWAIT_BLOCK_EXIT`. Do **not** check parked status inside `NibbleExecutor`; parked/arriving/finalizing is `MissionExecutor` responsibility.

## Mission executor look-ahead after nibble FSM changes

When nibble execution no longer completes immediately after MA refresh and instead waits for vehicle block exit, `MissionExecutor._handle_nibble_executing` must not run nibbles strictly one-at-a-time. If nibble N is active and waiting for block exit, nibble N+1 should already be started so it can sit in `AWAIT_BLOCK_ENTRY` and catch the vehicle entering the next block.

Recommended pattern:

- Keep a one-nibble look-ahead window.
- Start nibble N.
- Immediately start nibble N+1 with an `asyncio.create_task(...)` wrapper so it can register its entry listener.
- Await completion of nibble N before advancing the window.
- On active nibble failure, cancel any look-ahead tasks to avoid leaked background work.
- Add a regression test that proves N+1 starts before N completes, plus a failure-cleanup test that proves the look-ahead task is cancelled.

## Event-driven recheck pattern

When adding `AWAIT_BLOCK_EXIT`-style waits, register listeners for all authority-relevant status sources in the current/n+1 authority range, then transition back to route validation on relevant changes. For thalos this includes WSS route, block, signal, and bulletin state change events. Include ABS Direction only when that source is trusted; otherwise do not let ABS Direction trigger nibble rechecks or route-request wakeups. Make WSS status event emission deduplicate identical periodic status messages to avoid event storms.
