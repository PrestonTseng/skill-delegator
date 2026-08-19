# Windows Docker Desktop full-compose validation with preloaded local images

Use when the target host is Windows/amd64, application images already exist locally, but a non-interactive SSH session cannot pull/build because Docker Desktop's credential helper is tied to an interactive logon session.

## Repeatable pattern

1. **Use the exact requested application tags.** Put all image versions in a temporary env file consumed by the original Compose file. Record them in the final artifact.
2. **Keep the original Compose topology.** Add a small override file only for services whose images must be preloaded locally:
   ```yaml
   services:
     simulator-a:
       image: test/simulator-a:amd64
       pull_policy: never
   ```
   Start with `docker compose --env-file <run.env> -f docker-compose.yml -f <override>.yml up -d --no-build ...`.
3. **Build mock/test images for the host architecture at a location with source and registry access:**
   ```bash
   docker buildx build --platform linux/amd64 --load -t test/simulator-a:amd64 ./simulator-a
   docker save test/simulator-a:amd64 | gzip -1 > simulator-a-amd64.tar.gz
   ```
   Copy the archive to Windows and run `docker load -i ...`.
4. **Reset only isolated bind-mounted state.** If the remote checkout is a disposable archive/copy, remove its test DB directory before startup. Do not erase state in a shared checkout.
5. **Bring up prerequisites in dependency order:** broker/database; wait for health; run one-shot migration; then core services and simulators.
6. **Verify both liveness and the real cross-service interaction.** A service's HTTP health alone is insufficient. Verify the integration boundary (for example, a simulator's WebSocket connection plus receipt of a real command) and any state mutation/readback required by the test.
7. **Capture logs and inspect before teardown.** Use a unique project name, a run-specific output directory, `try/finally`, `docker compose down -v --remove-orphans`, then assert no containers remain for that project.

## Debugging rule

If a full-stack run surfaces a schema-validation error only after a cross-service message arrives:

1. Save the emitted payload or inspect the exact producer image/source.
2. Add a focused regression test that fails on the producer's actual value (including `null` where applicable).
3. Make the minimal compatibility change.
4. Rebuild for `linux/amd64`, reload, and repeat the same full-stack validation.

Do not treat a successful TCP/WebSocket handshake as proof of message compatibility; command parsing and acknowledgement must also succeed.
