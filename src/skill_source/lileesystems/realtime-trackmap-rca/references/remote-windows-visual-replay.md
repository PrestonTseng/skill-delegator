# Remote Windows visual replay quick path

Session learning from SART-2028 visual validation: if Preston asks to run a patch on the remote Windows machine for M1/M2/M3 visual inspection, optimize for getting the already-reviewed source running quickly. Do not burn time on registry/Docker Desktop credential helper workarounds unless the specific task requires validating the CI-published image.

## Preferred sequence

1. **Use source-overlay build when local source exists.**
   - Archive the approved local source (`git archive HEAD | gzip > ...`).
   - Copy the archive to the remote Windows RCA workspace.
   - Build a small overlay image from an already-present compatible Unicorn image on the remote host.
   - Copy only app source/config needed at runtime, not dependency installation layers.

2. **Avoid the Docker Desktop credential trap.**
   - SSH non-interactive sessions on Windows may fail `docker pull`/`docker build` metadata lookup with Docker Desktop `credsStore: desktop` errors.
   - Treat this as a setup blocker only if the task specifically requires registry pull. For visual validation, bypass by using local source over an existing base image.

3. **Keep the user-facing answer short when blocked.**
   - State the blocker in one sentence.
   - State the fastest workaround.
   - Do not narrate long experiments.

## Known-good overlay Dockerfile pattern

Use an existing remote Unicorn RCA image as the base:

```dockerfile
FROM unicorn:sart1929-master-queue-rca-amd64
WORKDIR /app
COPY src /app/src
COPY res /app/res
COPY pyproject.toml /app/pyproject.toml
```

Then build/tag on the remote Windows host, e.g.:

```powershell
docker build -f Dockerfile.overlay -t unicorn:sart2028-<commit>-amd64 .
```

## Replay correctness rules

- When replaying captured MQTT data for visual validation, preserve capture chronology: sort selected rows by capture timestamp ascending, with CSV id as the secondary key.
- Do **not** use `abs(capture_time - prev_time)` as a shortcut; it can hide reversed input order and make backward replay look plausible. Sleep only on positive forward deltas.
- If Preston asks for visual confirmation, prefer `speed=1` unless he explicitly asks for accelerated replay. Higher speeds are useful for stress envelopes, not for judging natural M1/M2/M3 motion.
- If the visible vehicle motion looks backwards or unnatural, inspect publish order before debugging frontend rendering or pubsub.

## Visual replay startup pattern

Use the existing RCA compose harness and set local images explicitly:

```powershell
$env:COMPOSE_PROJECT_NAME='sart2028visual'
$env:RCA_ROOT='C:/sart1929-rca'
$env:OUT_DIR='C:/sart1929-rca/out/<run-name>'
$env:UNICORN_IMAGE='unicorn:sart2028-<commit>-amd64'
$env:CRYSTAL_IMAGE='crystal:sart1929-0.21b2-rca-packet-amd64'
$env:MOSQUITTO_IMAGE='registry.lileesystems.com/eclipse-mosquitto:2.0.18-openssl'
$env:TIMESCALE_IMAGE='timescale/timescaledb:2.11.1-pg15'
$env:CRYSTAL_PORT='4200'
$env:UNICORN_PORT='8000'

docker compose -f C:/sart1929-rca/scripts/docker-compose.crystal-rca.remote.yml down -v --remove-orphans
docker compose -f C:/sart1929-rca/scripts/docker-compose.crystal-rca.remote.yml up -d mosquitto timescaledb
# run migration/init if the harness requires it
docker compose -f C:/sart1929-rca/scripts/docker-compose.crystal-rca.remote.yml up -d unicorn tools crystal
```

For Preston visual inspection, report ports/URLs immediately once containers are Up:

```text
Crystal: http://<remote-host>:4200/
M1:      http://<remote-host>:4200/m1
M2:      http://<remote-host>:4200/m2
M3:      http://<remote-host>:4200/m3
Unicorn: http://<remote-host>:8000/
```

## Pitfall

Do not spend many tool calls manually reconstructing Docker registry layers or fighting Docker Desktop credential helpers when the user asked for a quick visual run and the source code is already available. Build from copied source over a compatible local base image first.
