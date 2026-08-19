---
name: safeart-incident-rca
description: Investigate and publish SafeART/TAPAS production or Alpha incidents when symptoms cross Thalos, Unicorn/JPS, Crystal, MQTT, GraphQL, ADS, or WSS; use for release regressions, timeout/latency incidents, asyncio shared-runtime failures, and RCA reports that must link a Jira Bug to a sibling Confluence report.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [safeart, tapas, rca, incident, latency, asyncio, jira, confluence]
    related_skills: [lilee-confluence-adf-authoring, jira-ticket-writer, realtime-trackmap-rca, thalos-movement-rca]
---

# SafeART Incident RCA

## Purpose

Produce an evidence-bounded RCA for cross-service SafeART incidents, then publish a verified Jira Bug and Confluence RCA report without conflating the root defect with defensive mitigations.

The leading discipline is **causal ladder**: move from observed symptom, to measured regression, to changed runtime surface, to exact source mechanism, to controlled validation. Do not jump from a correlated log to a root-cause claim.

## Required Inputs

- incident environment and release/build;
- authoritative time window with timezone;
- affected workflow or API;
- production/Alpha logs and exact source revisions;
- comparison baseline when available;
- supplied RCA template or report location when publication is requested.

If a direct source is available, inspect it before relying on prior-session summaries.

## Workflow

### 1. Normalize the incident boundary

1. Convert the reported window to one authoritative timezone, normally UTC.
2. Record deployment/rollback boundaries and exact container/component versions.
3. Prefer unsaturated server-side log filters over broad queries capped by backend limits.
4. Separate independently reported symptoms before testing whether they share a cause.

**Complete when:** every decisive record can be placed on one timeline and every cited build maps to an exact revision.

### 2. Build comparable measurements

1. Define one latency or correctness measure that exists in both baseline and incident data.
2. State how timestamps are derived; distinguish caller start, server completion, and client timeout.
3. Report sample count, p50/p90/p95/p99/max, threshold exceedance count, and matching error count.
4. Keep caller-side timeout inference separate from server-side completion evidence unless raw client responses prove it.

**Complete when:** the regression is numerically established or explicitly remains unproven.

### 3. Map releases to component revisions

1. Resolve release tags to exact commits for every implicated service/library.
2. Identify the first changed release; do not assume the reported latest build introduced the defect.
3. Compare runtime dependency pins across packaging migrations.
4. Diff the failing endpoint path and shared-runtime paths separately.

**Complete when:** changed and unchanged candidate surfaces are enumerated with source evidence.

### 4. Climb the causal ladder

For each candidate, test in this order:

1. Did the directly failing endpoint change?
2. If not, what shared process, event loop, broker, database, or subscription path changed?
3. Can a production error name an exact coroutine/task/function created by that change?
4. Does the candidate explain all observed symptoms, including negative evidence?
5. What alternative candidates were excluded, and by what diff or measurement?

Rank conclusions as:

- **Proven** — direct production measurement, exact source match, or controlled reproduction.
- **High confidence** — changed shared-runtime surface that explains the evidence after alternatives are excluded.
- **Not quantified / not established** — contribution percentages or causal splits needing profiling or one-variable A/B.

**Complete when:** every material claim carries one of these evidence levels.

### 5. Design a falsifiable reproduction

1. Replay the same captured input rate and subscriber/client fanout in an isolated environment.
2. Hold workload, architecture, and sampling constant across baseline and candidates.
3. Change one mechanism at a time before testing a combined candidate.
4. Instrument event-loop lag, task lifecycle, publish/delivery counts, payload/copy cost, endpoint latency, and reconnects when relevant.
5. Define acceptance thresholds before running the candidate.

**Complete when:** another engineer can run the matrix and distinguish competing hypotheses.

For the asyncio/Unicorn pattern learned from a JPS latency incident, load `references/asyncio-shared-runtime-latency.md`.

### 6. Separate root repair from impact mitigation

- The root-cause Bug tracks the product defect.
- Defensive caller changes, bounded cleanup, retries, or idempotency belong in separate Tasks when they do not repair the defect.
- Link them with the strongest established Jira relationship; use `Relates` when no blocking/causal direction is proven.
- State explicitly which item reduces impact and which item repairs the root cause.

**Complete when:** ownership and validation scope are unambiguous in Jira.

### 7. Publish the RCA

When publication is requested, load both `jira-ticket-writer` and `lilee-confluence-adf-authoring`, then follow `references/confluence-rca-publication.md`.

Key order:

1. inspect template and sibling reports;
2. create/read back the Bug;
3. link separate mitigation Tasks;
4. create the ADF report under the template's exact parent;
5. read back both Jira and Confluence artifacts.

**Complete when:** the Bug fields, issue relationships, page parent, TOC-first structure, smart links, and required sections are all verified from live reads.

## Durable Record

Store task-specific evidence, scripts, metrics, and drafts in the canonical task plan directory. Keep the skill procedural; keep incident IDs and transient findings out of `SKILL.md`.

## Completion Checklist

- [ ] Timezone and incident window normalized
- [ ] Exact release/component revisions mapped
- [ ] Comparable baseline and incident metrics computed
- [ ] Direct endpoint diff checked
- [ ] Shared-runtime changes checked
- [ ] Error/coroutine signatures mapped to source
- [ ] Alternatives and evidence boundaries recorded
- [ ] One-variable reproduction matrix and acceptance criteria defined
- [ ] Root Bug separated from defensive Tasks
- [ ] Jira fields and links read back
- [ ] Confluence template parent and sibling conventions inspected
- [ ] New RCA page validated before creation and read back afterward
