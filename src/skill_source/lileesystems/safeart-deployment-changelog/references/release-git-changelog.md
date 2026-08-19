# Release Git Changelog Reference

Session seed: SafeART 0.21b3 Alpha changelog for `crystal`, `unicorn`, and `thalos`, prepared for dependency teams.

## Gerrit fetch pattern

If a repo fetch fails because the default SSH identity is not the Gerrit identity, fetch with the shared key:

```bash
GIT_SSH_COMMAND='ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' git fetch --all --tags --prune
```

This is a positive reusable pattern. Do not store "Gerrit fetch is broken" as a rule.

## Evidence commands

```bash
# Verify range endpoints
git rev-parse --short safeart-<previous>
git rev-parse --short safeart-<target>

# Count commits
git rev-list --count safeart-<previous>..safeart-<target>

# Commit messages + bodies
git log --reverse --date=short --pretty=format:'%h%x09%ad%x09%an%x09%s%d%n%b%n---ENDCOMMIT---' safeart-<previous>..safeart-<target>

# File-level impact
git diff --stat safeart-<previous>..safeart-<target>
git diff --name-status safeart-<previous>..safeart-<target>

# Focused inspection
git diff --unified=15 safeart-<previous>..safeart-<target> -- <paths...>
```

## Impact classification examples

### Crystal

Look for frontend changes that reveal backend dependency requirements:

- GraphQL subscription/query names changed in `*.gql.ts`.
- TypeScript response/event types changed in `*.type.ts`.
- UI now depends on static list queries plus live status subscriptions.
- Track-map UI changes may be display-only unless they imply data/API assumptions.

Example from 0.21b3:

- `subscribeBulletinList` changed to `subscribeBulletinChanges`.
- New event shape: `bulletinId`, `type`, optional `bulletin`.
- WSS Route Board uses `getTrackMapRouteList`, `getSignalList`, `getAbsDirectionList` and merges WSS setting/status onto those rows.

### Unicorn

Look for GraphQL, PubSub, config, REST, and build/runtime changes:

- `src/graphql_api/schema` and `resolver` indicate API/schema changes.
- `src/util/pubsub` indicates subscription semantics.
- `res/config.yml` indicates deployment/config defaults.
- REST client/handler diffs indicate HTTP error contract changes.
- Dockerfile/build/pyproject changes indicate CI/developer workflow impact.

Example from 0.21b3:

- PubSub delivery modes: `LATEST` for state-like streams, `ALL` for event-like streams.
- `subscribeBulletinChanges` replaces full-list bulletin subscription.
- `subscribeWaysideStatusFreshness` exposes `FRESH` / `STALE`.
- Safety Server timeout maps to HTTP `504`; config default `SAFETY_SERVER_CLIENT_TIMEOUT_SECONDS=10`.
- Build flow moved from pipenv/requirements to `uv`.

### Thalos / Safety Server

Look for Safety Server REST contract, route authority behavior, mission/MA/TSR behavior, and WSS/ADS-facing changes:

- API files show HTTP status/error contract changes.
- mission/nibble executor diffs show runtime movement/authority behavior.
- bulletin service diffs show TSR/Form/Bulletin behavior.
- WSS agent/model diffs show state-change events other services may observe indirectly.

Example from 0.21b3:

- Bulletin overlap enforce changed from HTTP `400` to `409`.
- Descending milepost ranges fixed by min/max overlap detection.
- Nibble route authority can reuse/request/revoke-and-request/wait based on WSS state.
- MissionExecutor syncs TSR to MA with locking and records applied/removed bulletin IDs.

## Output pattern

Use this shape for Discord:

```md
**SafeART <version> <env> deployment changelog — <repos>**

Source: git comparison `<prev>..<target>`.
Audience: teams depending on these services.

**Crystal**
- **<change title>**
  - Ticket: `<ticket>`
  - <what changed>
  - Dependency impact: <what another team must know/do>

**Unicorn**
...

**Thalos / Safety Server**
...

**Raw commit list**
...
```

Do not use markdown tables in Discord.
