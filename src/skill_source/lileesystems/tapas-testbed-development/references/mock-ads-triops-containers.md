# Standalone mock ADS / mock TriOps containers

This reference captures implementation decisions for TAPAS `tapas-testbed` standalone mock ADS and mock TriOps services.

## Durable design decisions

- Keep mock ADS and mock TriOps as standalone Python codebases inside `tapas-testbed`, managed by `uv`, and built directly by `docker-compose.yml` from repo source.
- One `mock-ads` container represents one vehicle. Add more compose services for more vehicles.
- Use `ASSET_ID` as the environment variable name for vehicle IDs and TriOps asset IDs, not `VEHICLE_ID`.
  - Example ADS asset IDs: `1.900.0001.01`, `1.900.0002.01`, etc.
  - Type 13 topic uses the TriOps asset id: `/v1/triops/setting/<ASSET_ID>`.
- Use `SAFETY_SERVER_WS_URL` for mock ADS command WebSocket configuration rather than reconstructing host/port fields.
- Disable Thalos in-process mocks when standalone testbed mock containers are active to avoid duplicate simulators.
- Store `mission_travel_time.json` in the mock ADS codebase and maintain it with git.
- Copy required Thalos const/track data into each mock codebase so mock ADS and mock TriOps can evolve independently; do not runtime-import Thalos.

## Mock TriOps scope

- First version does not implement Type 19.
- Track only block name and occupancy (`FREE` / `OCCUPIED`). Do not store vehicle id, reason, or source metadata in the occupancy state.
- Do not implement a transition API. Actual occupied state is reported by vehicles or future test-controller containers.
- Provide simple HTTP control/debug APIs: health, get all occupancy, get one block, put one block, reset, debug state.
- Publish Type 13 TriOps setting at 5Hz unless the user changes the rate.

## Mock ADS scope

- Initial state: vehicle appears directly in the configured parking area; `PARKING_AREA` should be an env var.
- VehicleStatus after returning to parking should be `READYTOGO`.
- ADS disconnect should close only the Safety Server WebSocket; MQTT Vehicle Status publishing continues.
- Publish Vehicle Status via MQTT to `/v1/obs/status/<ASSET_ID>`; do not add WebSocket status publishing unless explicitly requested.
- Match the current Thalos Vehicle Status model, not necessarily the latest ICD fields, unless the user asks for latest ICD compatibility.
- `MissionInfo.DelaySec` must default to `0`; do not use `null`.
- Door behavior is out of scope for first version; use safe/default fields only.
- `OperationMode` should not be changed to `ATO_STOP` just because the mock stops; keep the command-provided operation mode and expose stop reason through debug state.
- Yard/parking to `AV-1T` uses instant movement. Only service-line movement needs simulation.
- Block and sub-block must be handled together; some blocks have multiple sub-blocks.
- Service-line movement uses checked-in mission travel time, block/sub-block constants, facing signal state, next-block occupancy, and MA bounds.
- Milepost unit is 10 cm. Convert speed with `speed_mps = abs(delta_milepost_units) * 0.1 / delta_seconds`.
- `AuthorizedSpeed` is km/h; cap simulated m/s with `authorized_speed_kmh / 3.6`.
- `StartMp` and `EndMp` ordering can flip by direction. Always normalize for inclusion checks with `min(start,end)` / `max(start,end)`, and apply directional boundary logic separately.

## Verification pattern

Run verification inside the agent/container environment when LILEE VPN access is required. The user's host may not have VPN access, so pulling `registry.lileesystems.com` images from the host can fail. For local mock changes, prefer targeted builds that do not require pulling the whole registry-backed stack:

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

If a full-stack compose run requires pulling `registry.lileesystems.com` images and fails due to host/VPN scope, report the blocker and ask Preston to pull/provide the image rather than treating it as a code failure.

## Gerrit workflow reminder

Before pushing, use a SART Jira ID in the commit subject, e.g. `SART-XXXX Add standalone mock ADS and TriOps containers`, then push with:

```bash
git push origin HEAD:refs/for/master
```
