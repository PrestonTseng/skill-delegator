# Linux cross-repository candidate validation

Use this pattern when validating coordinated SafeART changes on a shared Linux AMD64 playground without publishing candidate images to the registry.

## 1. Inventory before mutation

- Connect read-only first and record hostname, `uname -m`, Docker/Compose versions, running Compose projects, and candidate working directories.
- Require an explicit project name and isolated ports, bind directories, network, and database. Do not reuse another run's database.
- If an old topology is reused, copy only compose/config/mock source. Exclude `data/` and `logs/`; root-owned bind data is both unsafe to copy and a source of false evidence.

## 2. Build and provenance

Prefer normal source builds:

```bash
docker buildx build --platform linux/amd64 --load -t <service>:candidate .
docker save <service>:candidate | ssh <vm> docker load
```

Pass private dependency credentials only as BuildKit secrets. Never copy a private SSH key into the VM or image layer.

### Exact stock-image overlay fallback

A private wheel or package endpoint may be reachable from the host/venv but not from a BuildKit network. Do not change dependencies merely to make the candidate build. A narrow source overlay is acceptable only when all of the following are true:

1. The repository's production diff is limited to a small set of source files.
2. A stock image matching the intended baseline exists on the AMD64 playground.
3. Extract each corresponding stock file with `docker create` + `docker cp`.
4. Compare it byte-for-byte (and record SHA-256) against `git show origin/master:<path>`.
5. Build `FROM` that exact stock image and `COPY` only the changed production files.
6. Record the stock digest, candidate image ID/architecture, local commit, changed files, and equality hashes.

If any baseline file differs, do not overlay; obtain/build the correct baseline instead.

## 3. Isolated Compose lifecycle

- Use an explicit project name, e.g. `docker compose -p <task-project> -f docker-compose.yml -f compose.override.yml`.
- Override candidate service images only; keep unchanged dependencies pinned to the tested stack versions.
- Bring up infrastructure first, wait healthy, run DB migration as a separate one-shot step, then start JPS/SS/mocks with `--wait`. This avoids Unicorn/migration startup races.
- Verify running image IDs and `linux/amd64` architecture before exercising behavior.

## 4. Behavior-first E2E

- Create schedules and missions through Unicorn public GraphQL/API, never by SQL mutation.
- Poll durable JPS state until the target lifecycle state is observed before acting.
- Exercise the user-facing cancellation path, record elapsed time, and read back durable state.
- For idempotency, retry after SS local ownership is gone and issue concurrent duplicate requests. Logs should prove one local terminal cleanup and goal-oriented no-ops thereafter.
- For strict failure semantics, make JPS unavailable while SS local state is already absent. Assert non-2xx; restore JPS and assert the same request succeeds. Use `docker pause` when a real client timeout (rather than immediate connection refusal) is required.
- Keep unit-test timing barriers for deterministic concurrency proof; VM latency alone is not proof that calls were concurrent or outside a lock.

## 5. Evidence and cleanup

Capture before teardown:

- API request/response JSON and timings
- durable JPS state read-back
- candidate image IDs, architecture, and baseline hashes
- complete relevant container logs, including unrelated noise rather than filtering it out
- Compose `ps` output

Then run `down -v --remove-orphans` and separately verify zero containers, networks, and volumes for the project label. If bind directories are root-owned and passwordless sudo is unavailable, use an already-present trusted container image with a `/tmp` bind mount to remove only the exact isolated directories. Verify those directories are absent afterward.
