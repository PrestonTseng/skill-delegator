---
name: tapas-knowledge
description: >
  Loads durable TAPAS / SafeART platform context: naming conventions, service catalog and ownership,
  core domain glossary, MQTT/ICD communication patterns, and authoritative reference links.
  Trigger when discussing TAPAS services (SS, MMS, JPS, ADS, WSS, TriOps, etc.), platform architecture,
  inter-service data flow, MQTT topics, or onboarding context.
---

# TAPAS Platform Knowledge

A knowledge primer for Lilee Systems' TAPAS platform. Loads when any TAPAS service or platform concept is mentioned, providing the **stable, slow-changing** parts of the platform: service catalog, ownership, glossary, communication patterns, ICD topic map, and authoritative reference URLs.

Volatile content (specific bug statuses, release contents, FSM internals) is intentionally **not** included — fetch live when needed. See *What's NOT in This Skill* below.

## Platform Naming (read inline — small)

| Term | Meaning |
|------|---------|
| **TAPAS** | Internal codename for the platform — the collection of services that together provide autonomous rail transit. Used in casual conversation, doc names, the ICD URL, and the dedicated Confluence space. |
| **SafeART** | External release / product name. Versioned (e.g. SafeART 0.18, 0.19, 0.20). What gets shipped to customers and what release notes describe. |
| **SART** | Jira project key and Cloud Team's Confluence space key. Tickets are `SART-XXXX`. |
| **T-Cloud** | "Cloud Team" — Preston's team. Owns most of the cloud-side and server-side services. |
| **ACES** | Sister team. Owns vehicle and trackside controllers (ADS, TriOps) and the original ARK Code design. |
| **LileeOS** | Legacy team name. Some services originally owned by LileeOS have transitioned to Cloud Team — currently WSS and OpenPLC. |

## Reference Guide

This skill is split into focused references. Read the one that matches the current task:

| Reference | When to read it |
|-----------|-----------------|
| `references/glossary.md` | Encountering an unfamiliar domain term (Mission, Nibble, MA, DOM, ARK Code, etc.) or doing onboarding-style explanations. |
| `references/services.md` | Need to know what a service does, who owns it, or how it fits in the system. Whenever a service name comes up. |
| `references/communication.md` | Discussing data flow, MQTT, ICD authority, inter-service interactions, or environments (Alpha / Pre-Alpha / Production). |
| `references/unicorn-realtime-subscription-rca.md` | Investigating realtime track-map latency through MQTT broker → Unicorn MQTT subscribers → InMemoryPubSub → GraphQL subscription → Crystal; includes broker replay, four-stage timing, and full-snapshot/coalescing pitfalls. |
| `references/icd-topics.md` | Need the MQTT topic name, publisher, frequency, or purpose for any of the 19 ICD types. Includes the ARK Code embedding note. |
| `references/ss-ark-code-design.md` | Discussing SS-side ARK Code architecture, categories, or broker/topic design proposals. |
| `references/tsr-behavioral-spec.md` | Need the distilled behavioral spec for TSR / Form A / Form B timing, enforcement, MA truncation, or offline/degraded handling. |
| `references/tsr-planning-source-hierarchy.md` | Planning TSR workstreams, maintaining delivery-map due-date / release-status fields, or backlog cuts and need the source hierarchy: spec-first, H1-as-history, due-date expression conventions, and which discussion pages are not authoritative for reshaping execution structure. |
| `references/tsr-delivery-map-gantt.md` | Turning the TSR Delivery Map into repeatable Gantt / dependency artifacts: Confluence ADF extraction, due-date/dependency parsing, PD/FE/BE Mermaid Gantt conventions, sidecar outputs, and verification. |
| `references/tsr-wording-conventions.md` | Need approved wording for Form A, Form B, and generic TSR diagrams and backlog artifacts, especially enforcement-off commands, boundary-hold MA labels, cross-diagram verb-pattern alignment, and source-faithful wording discipline. |
| `references/tsr-diagram-review-and-rendering.md` | Producing Mermaid review packs for TSR/Form A/Form B and need the accepted split between runtime vs GUI-operation diagrams, plus render-verification pitfalls like Mermaid syntax-error screenshots that still produce PNG files. |
| `references/tsr-release-note-framing.md` | Drafting TSR release-note sections and need the proven framing: 0.19 as baseline, 0.20 as control-layer hardening, later runtime scope explicitly out of claim, plus recommended screenshots / Mermaid packaging. |
| `references/door-psd-control-study.md` | Discussing mission timing vs door / PSD responsibility boundaries, stop-service semantics, or clean JPS/SS/ADS ownership wording in backlog/design docs. |
| `references/seshat-2-planning.md` | Shaping Seshat 2.0 specs, delivery maps, or tickets; includes phase model, realtime/history coexistence, Mission/MA timeline analysis, and the Type 3 virtual departure-signal boundary. |
| `references/realtime-trackmap-delay-rca.md` | Investigating realtime trackmap/subscription delay or burst delivery across ADS/WSS → MQTT broker → backend aggregator such as Unicorn → GraphQL/WebSocket → Crystal; includes broker-mediated replay and evidence-matrix workflow. |
| `references/crystal-trackmap-e2e-rca.md` | Extending realtime track-map RCA into real Crystal/browser rendering: Codebase Memory inspection, 0.21b2 baseline worktree, frontend telemetry seams, Playwright collection, per-record publish-to-render joins, and presentation chart patterns. |
| `references/sart1929-mqtt-replay-thresholds.md` | Session-specific SART-1929 notes on MQTT replay threshold testing, Alpha broker image parity, Mosquitto drop-log interpretation, and why 10x synthetic replay should not be treated as Alpha root cause without Alpha timing evidence. |

It is fine — and often correct — to read multiple references in one task. When in doubt, read `services.md` first; it grounds everything else.

## Stable IDs & Authoritative URLs

| What | Value |
|------|-------|
| Atlassian site | `lileesystems.atlassian.net` |
| Atlassian cloudId | `302f7dfa-a172-4986-b4ae-efd7021f110a` |
| Preston's accountId | `712020:350e731b-9f7b-4fd9-91d4-70bffe6e4af8` |
| Jira project key | `SART` |
| Confluence space — Cloud Team | `SART` (https://lileesystems.atlassian.net/wiki/spaces/SART) |
| Confluence space — Platform | `TAPAS` (https://lileesystems.atlassian.net/wiki/spaces/TAPAS) |
| ICD website | http://10.2.10.51/icd/latest/ |
| ICD source (Gerrit) | https://lilee-ci-tw.lileesystems.com/gerrit/plugins/gitiles/devops/tapas-icd/+/refs/heads/master |
| Alpha env reference | https://lileesystems.atlassian.net/wiki/spaces/TAPAS/pages/2731540565/Alpha |
| Pre-Alpha (tapas-testbed) repo | https://lilee-ci-tw.lileesystems.com/gerrit/admin/repos/tcloud/test/tapas-testbed,general |
| Pre-Alpha README | https://lilee-ci-tw.lileesystems.com/gerrit/plugins/gitiles/tcloud/test/tapas-testbed/+/refs/heads/master/README.md |

## Companion Skills

This skill provides context. Other skills do work on top of that context:

- **`jira-ticket-writer`** — drafts and pushes SART tickets following Cloud Team's Task / Story / Bug structures.
- **`release-commit-summary`** — generates SafeART release commit summaries from the H1 KPI page.
- **`grill-me`** — stress-tests technical proposals before committing.

## What's NOT in This Skill

Deliberately excluded because too volatile or out of scope:

- **Specific bug / defect statuses.** Check the SART board live.
- **Release content / what's-in-this-release.** Use `release-commit-summary`.
- **FSM internals beyond high-level state names.** Fetch from Confluence design pages on demand.
- **MQTT payload schemas.** Fetch from tapas-icd live (`references/icd-topics.md` has the topic catalog; payloads stay in ICD).
- **Hermes / hermes-tapas.** Separate Discord agent tooling, not part of TAPAS.
- **Tooling stack (Obsidian, n8n, Claude Code plugins, etc.).** Out of scope here.

## Maintenance

When information drifts:

- **Ownership change** (a service moves between teams) → update `references/services.md`.
- **New service** → add an entry to `references/services.md` under the correct team section.
- **Glossary term refined / added** → append to `references/glossary.md`.
- **New ICD type** or topic rename → update `references/icd-topics.md` (and verify against ICD source).
- **Reference URL changes** → update the *Stable IDs* table in this file.
- **A "TBD" gets resolved** → replace with the resolved content.

Avoid embedding release-version-specific facts here; those belong in release notes or release-commit summaries.
