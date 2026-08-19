# SART-1929 human-readable RCA format lesson

## What triggered this reference

During the SART-1929 Crystal M1/M2/M3 realtime trackmap RCA, the first Confluence write-up was technically detailed but too much like an evidence dump / AI-oriented report. Preston corrected the format: the page should primarily be for human readers, should match sibling RCA report structure, and should use diagrams to show where timing gaps occur rather than relying mainly on tables.

## Correct structure for SART-style RCA pages

Inspect sibling pages under the same RCA parent before writing. For the SART RCA report family, mirror this shape:

1. `Reported by ACES Team`
2. `Bug Ticket` with Jira smart link
3. TOC
4. `TL;DR`
5. `Issue`
6. `Root Cause Analysis`
7. `Reproduce / Validation Steps`
8. `Repair Suggestions`
9. Optional appendix / expands for detailed packet metrics

Avoid leading with a large hypothesis table. Use the table only as appendix or when it directly helps the reader.

## Human-first RCA narrative pattern

Use this ordering in the main page body:

1. **What the user saw** — short field symptom in plain language.
2. **Where the gap/failure is located** — visual pipeline diagram.
3. **How we proved it** — one-variable A/B evidence, minimal numbers.
4. **Root cause mechanism** — simple sequence diagram or step-by-step failure path.
5. **What it is not** — short falsification list.
6. **Repair suggestion** — concrete production direction and caveats.
7. **Detailed metrics** — expandable appendix.

## Useful visual blocks

### Pipeline gap localization

```text
MQTT replay publisher       Mosquitto        Unicorn MQTT handler       InMemoryPubSub       GraphQL WS       Crystal render
       │                       │                    │                         │                 │               │
       │  publish cadence OK   │                    │                         │                 │               │
       ├──────────────────────►│                    │                         │                 │               │
       │                       ├───────────────────►│  handler path OK        │                 │               │
       │                       │                    ├────────────────────────►│                 │               │
       │                       │                    │                         │  GAP / LOSS     │               │
       │                       │                    │                         │  coalesce +     │               │
       │                       │                    │                         │  lost wakeup    │               │
       │                       │                    │                         ├────────────────►│  receives fewer snapshots
       │                       │                    │                         │                 ├──────────────►│ render fast

Supported gap location: Unicorn InMemoryPubSub → GraphQL subscription delivery boundary.
```

### Publish-vs-delivered summary

```text
Current event/latest-value mode
  MQTT/Unicorn vehicle publishes:      ████████████████████████████████████████ 4010
  Crystal subscription snapshots:      ██████████                               ~1038

Diagnostic queue mode
  MQTT/Unicorn vehicle publishes:      ████████████████████████████████████████ 4010
  Crystal subscription snapshots:      ████████████████████████████████████████ 4010

Clear-before-yield diagnostic
  Crystal subscription snapshots:      ███████████████████                      1950
```

### Lost-wakeup sequence

```text
Subscriber                         Publisher                         Crystal
----------                         ---------                         -------
await event.wait() returns
read latest snapshot A
yield A  ───────────────────────────────────────────────────────────► receives A
                                   publish snapshot B
                                   latest_topic_value = B
                                   event.set()
resume after yield
event.clear()   ← clears B's wakeup
await event.wait() sleeps
                                   publish snapshot C
                                   latest_topic_value = C
                                   event.set()
wake, read C
yield C  ───────────────────────────────────────────────────────────► receives C

Snapshot B was overwritten/hidden. Crystal sees A → C and the vehicle jumps.
```

## Style rules

- Prefer short paragraphs and code-block diagrams over dense tables.
- Keep detailed p95/p99/max metrics in an appendix or expand.
- Preserve original tester work as `Original observations`, not as the final conclusion.
- Use precise confidence wording: `primary supported root cause`, `strongly supports`, `diagnostic only`.
- If a diagnostic queue proves causality, still say it is not a production patch unless it is bounded and has an explicit drop/backpressure policy.
