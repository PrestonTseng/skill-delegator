# Remote Windows Compose Testing for tapas-testbed

Use this reference when Preston offers the Windows AMD64 host `10.2.8.144` to verify `tapas-testbed` changes.

## When to use

Use the Windows host when:

- local host architecture or Docker environment may differ from expected deployment/testing conditions;
- registry pulls or image builds need an amd64 Windows Docker Desktop environment;
- the change touches `docker-compose.yml`, local build contexts, port mappings, or standalone mock containers.

## Recommended approach

1. Connect with the shared Gerrit SSH key when available:

   ```bash
   ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared \
     -o IdentitiesOnly=yes \
     -o StrictHostKeyChecking=no \
     preston.tseng@10.2.8.144 "cmd /c whoami && hostname && docker --version && docker compose version"
   ```

2. Stage the exact committed source rather than copying an ad-hoc working tree:

   ```bash
   cd /opt/data/workspace/tapas-testbed
   git archive HEAD | ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared \
     -o IdentitiesOnly=yes -o StrictHostKeyChecking=no \
     preston.tseng@10.2.8.144 \
     "tar -xf - -C C:/Users/preston.tseng/hermes/tapas-testbed-<task>"
   ```

3. Use a dedicated Compose project name and non-default host ports to avoid collisions:

   ```powershell
   $Project = 'sart2034mocktest'
   docker compose -p $Project --env-file .env.<task> config --services
   docker compose -p $Project --env-file .env.<task> build mock-triops mock-ads-1
   docker compose -p $Project --env-file .env.<task> up -d mosquitto thalos mock-triops mock-ads-1
   ```

4. Verify service APIs, not just container startup:

   ```powershell
   Invoke-RestMethod http://localhost:18100/health
   Invoke-RestMethod http://localhost:18101/health
   Invoke-RestMethod http://localhost:18100/occupancy/AV-1T
   Invoke-RestMethod -Method PUT http://localhost:18100/occupancy/AV-1T \
     -ContentType application/json \
     -Body (@{ occupancy = 'OCCUPIED' } | ConvertTo-Json)
   Invoke-RestMethod http://localhost:18101/vehicle-status
   Invoke-RestMethod http://localhost:18101/debug/state
   ```

5. Always collect artifacts and clean up:

   ```powershell
   docker compose -p $Project logs --no-color --tail=300 > compose-logs-tail.txt
   docker compose -p $Project down -v --remove-orphans
   docker ps -a --filter "label=com.docker.compose.project=$Project" --format '{{.Names}}'
   ```

   Treat an empty final container list as the cleanup verification.

## Docker Desktop / SSH-session pitfall

On Windows Docker Desktop, `docker context ls` may show `desktop-linux`, but SSH sessions can still fail if the Linux engine pipe is not running:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
Docker Desktop is unable to start
```

If this happens:

- start `com.docker.service` if needed;
- try launching Docker Desktop, but do not treat a failed engine pipe as a code/test failure;
- ask Preston to start Docker Desktop interactively or confirm the Docker daemon/context available to SSH sessions;
- record cleanup status and leave a rerunnable PowerShell script on the remote host.

## Evidence to report

Report:

- remote source path;
- Compose project name;
- output/artifact directory;
- Docker/Compose versions;
- exact pass/fail point;
- API verification outputs;
- cleanup verification result.
