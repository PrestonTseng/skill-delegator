# Dispatcher Workstation Page Architecture

Use this reference when a TAPAS redesign task asks which user-facing pages a dispatcher needs, what each page does, what Crystal already provides, and what remains missing.

## Product distinction

- **M1-M3 today** means three physical screens that show real-time vehicle and wayside information in Crystal.
- **M1-M3 Dispatch Workstation** (short form: **Dispatch Workstation**) is the future dispatcher interface for site-wide control, including emergency operation.
- M1, M2, and M3 are not roadmap phases, maturity levels, or fixed workflow roles.
- Treat the screens as display surfaces and the pages as logical work views.
- Do not assign a fixed page to a screen unless an approved operating study defines that layout.

## User-first analysis sequence

Do not start the review page with repositories, services, or KISS/full-target architecture chapters. Use this sequence:

1. List the complete end-state page inventory.
2. For each page, state the dispatcher goal.
3. List the functions that the dispatcher needs on that page.
4. Map current Crystal pages and controls to those functions.
5. State missing or required changes.
6. Give observable acceptance criteria.

Use one fixed structure for every page:

```text
Page name
├── User goal
├── Functions
├── Current Crystal support
├── Missing work
└── Acceptance criteria
```

If the user asks for full-roadmap scope, omit a KISS section. Do not force short-term and long-term scope labels into a user-journey document.

## Recommended main page inventory

Use this as the default starting hypothesis:

1. **Field Overview** — complete site topology and direct train, route, signal, switch, track, sector, platform, restriction, and bulk control.
2. **Incident Command** — incident lifecycle, phase, ownership, hold, decisions, approvals, handover, and closure.
3. **Service and Recovery** — service freeze, cancellation/reschedule, restriction lifecycle, inspection, proving movement, recovery gates, staged reopening, and rollback.
4. **Passenger Management** — passenger disposition, train doors, PSD, detraining, evacuation, accessibility support, and station handover.
5. **Command History** — command lifecycle, per-target result, approval, proof, rollback, replay, and export.
6. **System Health** — source/service health, data age, validity, trust, conflicts, impact, and degraded-operation rules.

Important classification:

- Fleet Control and Wayside Control are **capabilities inside Field Overview**, not peer pages.
- Emergency Movement is a protected workflow launched by selecting a train and route on Field Overview, not a permanent first-level page.
- TSR spatial selection belongs on topology; restriction lifecycle and service impact belong in Service and Recovery.
- Separate pages are reserved for durable multi-step workflows, broad coordination, audit, and diagnosis.

## Topology-first interaction rule

**Field Overview topology is the primary operating surface**, not a read-only overview or merely a launcher for control pages.

Routine operations happen directly on selected topology objects:

- Train: Stop, Hold, Release, DOM, disposition, Emergency Movement.
- Signal: choose route origin/destination, preview, request, cancel, release.
- Switch: inspect position/lock/occupancy and request a permitted position change.
- Block / track / sector: closure, reopening, TSR, inspection zone, protected corridor.
- Platform / PSD / power asset: inspect state and request permitted actions.

Use this interaction sequence:

```text
Select topology object(s)
→ show valid actions and disabled-action reasons
→ preview route / scope / conflicts / authority boundary on topology
→ confirm and approve
→ show requested / accepted / executed / physically proved states separately
```

A contextual popup may collect parameters, reason, approval, and confirmation, but topology remains the operating surface. Use multi-select, sector selection, filters, or drawing tools for fleet-wide commands and area restrictions. Show one result per target.

## Current Crystal mapping pattern

Verify against the pinned repository revision before use. Compare interaction capability; do not mechanically map every current route to a future page:

- M1/M2/M3 track maps → Field Overview foundation, but split by site segment and primarily display-oriented.
- Vehicle Management → source capability for direct train controls and bulk DOM on Field Overview.
- Route Board → source capability for direct signal, route, switch, and block operations on Field Overview.
- Manual Mode → source capability for Emergency Movement launched and monitored from Field Overview.
- TSR → spatial drawing/affected-area selection on Field Overview; lifecycle and service impact in Service and Recovery.
- Plan, Preview, Conflict, and Detailed Schedule → Service and Recovery.
- Schedule Audit → a small part of Command History.
- No current page fully covers Incident Command or System Health; inspection and staged recovery are also missing from Service and Recovery.

Do not infer operational completeness from a visible UI control. Trace its backend command, failure propagation, acknowledgement meaning, applied state, and physical proof.

## Cross-screen requirements

- Any logical page can open on any physical screen.
- Screens share the selected incident, sector, train, route, asset, and command context.
- Each screen can preserve independent zoom and filters.
- The workstation can pin or send a page/object to another screen.
- Restart restores the previous layout and active incident context.
- The product team must decide whether Field Overview stays permanently visible on one screen.

## Cross-page requirements

- A global header shows incident, phase, owner, hold, closures, alarms, unresolved commands, and trust.
- The same object-detail model opens from maps, lists, search, alarms, and command history.
- Requested state and observed state are separate.
- Safety-critical data shows source, observation time, receive time, age, validity, trust, and reason.
- Missing, stale, or conflicting data is `UNKNOWN`, never implicitly safe.
- High-impact commands use preview, permission, confirmation, command ID, per-target result, timeout, rollback, and audit.
- The UI sends intent through TAPAS services and interlocking. It does not write PLC registers directly.

## Acceptance-criteria quality

Acceptance criteria must describe user-visible and system-verifiable outcomes. Include abnormal behavior.

Good examples:

- The page accounts for every expected train before it reports fleet stop complete.
- A bulk command shows one result for every target train.
- The route page does not show `PROVED` until observed field state matches the request.
- A failed source changes affected data to `UNKNOWN` within its configured threshold.
- Restart restores the active incident, ownership, holds, closures, commands, and unresolved actions.

Avoid criteria such as “supports emergency control” or “works correctly.”

## Review-page publishing

- Publish as `IN REVIEW` until explicit approval.
- Keep TOC as the first top-level ADF node.
- Use native status controls for `IN REVIEW`, `PARTIAL`, and `MISSING`.
- Keep detailed file/symbol evidence in plan evidence or an appendix.
- Read back the page and count the expected logical page sections and repeated subheadings.
- Do not add unapproved conclusions to the parent summary.
