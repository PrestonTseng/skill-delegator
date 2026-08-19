# Windows Docker Desktop over SSH: compose validation workaround

Use this reference when a compose/runtime validation must run on a remote Windows AMD64 host via SSH and Docker Desktop is involved.

## Symptom

From an SSH session, Docker CLI can see the Windows Docker Desktop context, but build/pull fails with credential-helper or session errors such as:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
Docker Desktop is unable to start
error getting credentials - err: exit status 1, out: `A specified logon session does not exist. It may already have been terminated.`
```

This can happen even after `com.docker.service` is running and Docker Desktop is usable interactively. It is especially common when the user's `~/.docker/config.json` uses:

```json
{
  "credsStore": "desktop",
  "currentContext": "desktop-linux"
}
```

The SSH session may not have the interactive logon session required by Docker Desktop's credential helper.

## Reliable workaround for code under test

When the goal is to validate locally modified services and the remote host is Windows AMD64:

1. Build Linux/amd64 images from the Hermes/container side where network and source access are available:

```bash
docker buildx build --platform linux/amd64 --load -t <project>/<service>:amd64 ./path/to/service
```

2. Save and compress images:

```bash
docker save <project>/<service-a>:amd64 <project>/<service-b>:amd64 | gzip -1 > /opt/data/tmp/<project>-images-amd64.tar.gz
```

3. Copy to Windows host and load:

```bash
scp -i /opt/data/shared/ssh/id_ed25519_gerrit_shared /opt/data/tmp/<project>-images-amd64.tar.gz user@host:'C:/Users/<user>/hermes/<project>-images-amd64.tar.gz'
ssh -i /opt/data/shared/ssh/id_ed25519_gerrit_shared user@host 'cmd /c docker load -i C:\Users\<user>\hermes\<project>-images-amd64.tar.gz'
```

4. Run a temporary compose file on the remote host that uses the loaded images and avoids pulls:

```yaml
services:
  service-a:
    image: <project>/service-a:amd64
    pull_policy: never
```

5. Use a unique compose project name, collect logs/artifacts, and always cleanup:

```powershell
docker compose -p <project> -f compose-remote.yml up -d
docker compose -p <project> -f compose-remote.yml logs --no-color > logs.txt
docker compose -p <project> -f compose-remote.yml down -v --remove-orphans
docker ps -a --filter "label=com.docker.compose.project=<project>" --format '{{.Names}}'
```

## What to record

- Remote hostname, Docker client/server version, server `OS/Arch`.
- Exact compose project name.
- Remote output directory.
- Which images were loaded locally vs pulled.
- Which services were intentionally omitted because private registry pulls were blocked.
- Cleanup verification output.

## Pitfall

Do not conclude the service under test failed if Docker Desktop cannot pull/build from SSH due to `credsStore: desktop`. Separate Docker credential/session failure from application runtime validation. Prefer loaded-image validation for the code under test, and explicitly label any omitted dependencies as validation limits.
