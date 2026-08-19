# Manual-Control Support Audit

Use this reference when comparing current Unicorn/Crystal capabilities with an approved emergency, earthquake, degraded-operation, or dispatcher manual-control design.

## Audit boundary

- Pin exact repository commits before making claims.
- Check for a dirty working tree. Audit committed `HEAD`; do not accidentally treat unrelated local instrumentation as shipped support.
- Distinguish four levels: **Supported**, **Strong primitive** (core command exists but governance/workflow is missing), **Partial**, and **Missing**.
- For negative findings, search both repositories by domain term and structural concept: `incident`, `hold`, `command_id`, `approval`, `freshness`, `inspection`, `proving`, and lifecycle/state-machine symbols.

## Capability matrix

Evaluate at least:

1. Incident declaration, ownership, milestones, and closure.
2. Train census, status reconciliation, and non-reporting vehicles.
3. Fleet stop and positive stop proof.
4. Persistent hold and governed release independent of mission timeout.
5. Emergency/restricted movement authority.
6. Mission lifecycle controls and ad-hoc/manual dispatch.
7. Suspend/cancel/replan and recovery planning.
8. Protected corridor lifecycle and conflicting-route exclusion.
9. Route/wayside control and proof.
10. TSR/bulletin lifecycle.
11. Inspection, proving, and staged recovery.
12. RBAC, approval, audit, command acknowledgment, and idempotency.
13. Trusted-data/freshness handling.
14. Bulk operations and partial-failure reconciliation.

## Full-stack audit extensions

For Thalos/WSS/ICD/topology audits, also evaluate:

- event enum and DOM mapping parity across live ICD, runtime handler, API prose, and tests;
- the full command chain: GUI intent → backend permission → Thalos owner/correlation → WSS or ADS request → wire ACK → periodic status proof → physical proof → operator-visible final result;
- the actual source of a global-operation target list. A command/MA cache is not proof of all connected vehicles, and a connected list is not an authoritative all-train census. Reconcile expected, connected, reporting, stale, unknown, and non-reporting vehicles;
- whether lower-layer reject/timeout results propagate to the upper API. Logging a failure is not enough if REST/GraphQL still reports success;
- whether emergency hold and movement are persistent first-class objects or merely fields refreshed inside a timed mission;
- WSS health gating, UNKNOWN semantics, route owner, switch state/command support, per-command result/reason, and restart behavior;
- what WSS ACK proves: parse receipt, accepted intent, PLC execution, or physical field state. Check correlation/sequence IDs, end-to-end ACK consumers, and whether pending request values can be echoed as observed state;
- door/PSD runtime handling separately from schema presence: mission handlers, WSS status caching, command correlation, physical-state proof, and passenger handover;
- deployed Structured Text separately from a topology/YAML foundation branch. Read the foundation README and generated-artifact inventory before claiming it drives runtime;
- duplicated topology across Thalos constants, Unicorn TSV constants, Crystal visualizer data, WSS ST/mappings, and a candidate SSOT branch;
- interface-change minimization: first determine whether existing Type 2 status, Type 3 non-service MA/range/speed/DOM, and Type 4 ACK can support a KISS emergency-control slice. Preserve payload compatibility when possible, but still require explicit external semantics for STOP, HOLD, MOVE, PAUSE, RESUME, CANCEL, validity, reconnect, and failure reporting.

## Evidence rules

- Cite exact file paths, symbols, API/GraphQL operations, and line ranges where available.
- Treat tests as evidence of intended behavior, not proof of deployment or operational completeness.
- Separate external-system behavior from repository ownership. An E2E test that triggers an external severity event proves integration, not that Unicorn/Crystal owns incident management.
- A synchronous HTTP/GraphQL success is not a durable command acknowledgment without a command ID and requested/accepted/applied/rejected reconciliation.
- A braking/degraded-operation mode is not automatically a persistent hold.
- A route authorization primitive is not automatically a protected corridor.
- Schedule approval/audit is not operational-command approval/audit.
- Telemetry is not trusted operational data unless freshness/disconnection is exposed and acted upon.

## Common TAPAS interpretation traps

- Mission lock/start/complete/cancel REST endpoints may be SS integration callbacks rather than dispatcher controls; inspect authentication and transition role.
- Manual dispatch may still generate timed service groups/missions. Do not call it full manual movement control without proving independence from timeout semantics.
- A DOM command or interface ACK is not stop/hold proof. Separate requested, sent, received, accepted, applied, physically confirmed, and completed states.
- A WSS route setting ACK may occur before PLC execution or field proof. Do not promote it to `PROVED` without status correlation and an end-to-end consumer.
- Schema fields for door/PSD status or settings do not prove working handlers or physical completion.
- Check Crystal page guards/button gating separately from backend mutation authorization.
- Emergency controls require dedicated permissions; reusing vehicle CRUD permissions is a governance gap.
- Inspect which response fields Crystal actually requests; backend state returned but discarded by the UI is weak feedback.

## M1-M3 workstation terminology

- `M1-M3` is one workstation/display name comprising three real-time screens for track topology, wayside state, and vehicle state.
- Never present M1, M2, and M3 as roadmap stages, maturity levels, or separate backlog items.
- Do not invent the per-screen allocation. Record the purpose, track area, information density, alarms, and command placement as open design work until Preston confirms them.
- Treat route, switch, incident, restriction, and audit functions as shared workstation/backend capabilities rather than assigning them to numbered phases.

## Review-page packaging

When the audit is ready for Confluence review:

1. Put the decision summary, current capability, critical gaps, KISS option, full target, interface boundary, M1-M3 requirements, delivery order, and review decisions in the main body.
2. Keep raw file/symbol evidence and the full requirement matrix in the canonical plan evidence or a page appendix.
3. If Preston asked for a page before approval, mark it `IN REVIEW`, state that conclusions are not approved, and do not update the parent’s approved summary.
4. Read back the page and verify TOC-first, status, title, parent, and the corrected M1-M3 wording.

## Recommendation format

### KISS extension

Reuse existing command and telemetry services; add a small persisted incident state machine, append-only operational-command receipts, dedicated permissions, incident/reason linkage, idempotency, per-target results, freshness checks, and approval gates. Compose existing Crystal panels into one incident workspace. Keep vital safety decisions in Safety Server/WSS/SS; Unicorn orchestrates and audits intent/results.

### Full refactor

Separate telemetry projections, command intent, asynchronous receipts, protection state, approvals, and recovery workflow into an incident-command orchestration module. Model emergency movement as a governed movement request rather than a special timed service group. Use a typed incident feature shell/store in Crystal.

## Completion report

State audited commits, dirty-tree treatment, whether tests were executed or only inspected, source limitations, and whether files changed.