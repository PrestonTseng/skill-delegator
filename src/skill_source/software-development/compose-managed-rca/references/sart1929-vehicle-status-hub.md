# SART-1929 VehicleStatusHubSubscriber Isolation Case Study

## Context

A performance RCA investigated Crystal track-map delay across MQTT broker → Unicorn → GraphQL subscription → Crystal render.

The user corrected the workflow: any task that starts multiple Docker containers must use Docker Compose, and tests must run `compose down` afterward so no garbage containers remain.

## Durable Lessons

### Use Compose for multi-container RCA

The stack had broker, DB, Unicorn, Crystal, tools/replay, and Playwright collector containers. Compose made runs repeatable and allowed safe cleanup with:

```bash
docker compose down -v --remove-orphans
```

A run script should collect logs in `finally`/trap before teardown, then verify no project containers remain.

### Separate lab overload from production RCA

Synthetic replay produced Mosquitto:

```text
Outgoing messages are being dropped for client ...
```

But Alpha production broker logs did not contain that message. The right conclusion was not “Alpha root cause is broker drop.” The right conclusion was:

- lab overload shows a failure mode and where it appears;
- production RCA still needs production-equivalent per-stage timing;
- absence of the production log demotes, not deletes, the hypothesis.

### Architecture/image parity matters

Alpha broker image was:

```text
registry.lileesystems.com/eclipse-mosquitto:2.0.18-openssl
```

It was amd64. Running that image locally on an arm64 host would introduce emulation, so performance comparisons used a remote amd64 Docker host.

### Find the stable envelope before stress conclusions

Single-page `/m1` tests showed:

- lower-rate runs can be stable;
- higher-rate runs can create artificial broker/client overload;
- threshold mapping is for calibrating the harness, not for proving production RCA.

### One-variable isolation can reveal hidden amplifiers

Code inspection found two MQTT consumers over `/v1/obs/status/*`:

1. `VehicleStatusSubscriber`
   - main `/v1/obs/status/+` subscriber;
   - feeds realtime vehicle GraphQL subscription / Crystal track map.

2. `VehicleStatusHubSubscriber`
   - creates per-vehicle MQTT clients;
   - client id format: `vehicle_status_hub_subscriber_<ads_id>`;
   - subscribes `/v1/obs/status/<ads_id>`;
   - feeds the ark-code path.

A/B test on remote amd64 + Alpha broker image + `/m1` + 5x replay:

**Hub enabled**

- Main Unicorn MQTT received only ~4.4k / 18k vehicle rows.
- Mosquitto drop logs appeared.
- publish→Unicorn and pubsub→Crystal showed multi-second/huge delays.
- Unicorn handler/pubsub and Crystal render stayed fast.

**Hub disabled** with:

```text
ENABLE_VEHICLE_STATUS_HUB_SUBSCRIBER=false
```

- Main Unicorn MQTT received 18k / 18k vehicle rows.
- Mosquitto drop logs: 0.
- publish→Unicorn p95 was low-ms/teens-ms scale.
- pubsub→Crystal and render were stable.

This isolated `VehicleStatusHubSubscriber` as a lab overload amplifier.

### Verify whether the suspect is in-path or only shared-source

A later source-code check refined the conclusion. `VehicleStatusHubSubscriber` was not in the Crystal M1-M3 application path:

```text
VehicleStatusSubscriber
→ PubSubTopic.REALTIME_VEHICLES
→ GraphQL subscribeRealtimeVehicle
→ Crystal M1/M2/M3 track map
```

The hub path was separate:

```text
VehicleStatusHubSubscriber
→ vehicle_status_hub package
→ RealtimeVehicleArkCodeHandler
→ PubSubTopic.REALTIME_VEHICLE_ARK_CODES
→ GraphQL subscribeRealtimeVehicleArkCode
→ vehicle-management Ark Code UI
```

The coupling was at the shared MQTT source, not the application pubsub/render path:

```text
/v1/obs/status/<ads_id>
  +-- main wildcard subscriber: /v1/obs/status/+
  +-- hub per-ADS subscribers: /v1/obs/status/<ads_id>
```

The hub package came from an installed wheel in `requirements.txt`. To verify behavior, inspect the exact installed source, either by extracting the wheel or by introspecting inside the built image. In this case, `vehicle_status_hub/RemoteAutomatedDrivingSystem.py` showed one Paho MQTT client per ADS, `loop_start()`, and `client.subscribe(self.topic, qos=1)`.

This distinction matters: do not claim a side component is “in the failing path” just because toggling it changes the symptom. It may be a shared-resource amplifier.

## How to Reuse This Pattern

When a full-stack replay shows a bottleneck before application processing:

1. Confirm all consumers of the same broker topics.
2. Identify duplicate/per-entity subscribers that may amplify broker/client load.
3. Add feature-flag toggles to Compose, not production code.
4. Run A/B with only that component changed.
5. Compare counts and stage p95/p99/max.
6. Keep production-equivalence caveats explicit if production logs differ.

## What Not to Persist as a Rule

Do not record “Mosquitto drop is the root cause” as a general rule. In this case Alpha lacked the drop log. The reusable rule is the method: Compose-managed A/B isolation plus per-stage timing.
