# TSR Release-Note Framing (SafeART 0.20 draft lesson)

Use this reference when drafting TSR sections in SafeART release notes.

## Source hierarchy for release-note claims
1. **Behavioral truth:** `Backlog - Temporary Speed Restriction (TSR)` (Confluence page `3714482215`)
2. **Packaging / release slice:** `Temporary Speed Restriction (TSR) Delivery Map` (Confluence page `3796664324`)
3. **Execution status check:** live Jira status for the story / task tickets referenced by the Delivery Map

Do **not** let discussion pages or refinement notes override the spec / delivery-map split when deciding what the release can claim.

## Core framing lesson from the 0.20 TSR draft
For SafeART 0.20, the safest high-level packaging is:
- **0.19 baseline:** Bulletin CRUD + Manual Enforcement ON/OFF
- **0.20 landed TSR layer:** timer setup, overlap blocking, bulletin lifecycle logging
- **not part of the 0.20 delivered claim:** MA push & vehicle ACK visibility, trackmap rendering, persistent labels, overspeed, Form A / Form B runtime handling, signal-based authorization, per-block advisory validation

In short: frame 0.20 TSR as **dispatcher-side control-layer hardening**, not as a full end-to-end TSR runtime release.

## Why this framing works
It matches both:
- what the Delivery Map groups into the 0.20 TSR slice, and
- what live Jira status actually supports as Done.

This avoids over-claiming vehicle-facing or runtime behavior that is still To Do / In Progress.

## Drafting pattern
When writing the TSR section:
1. State the 0.19 baseline explicitly so readers know what was already present.
2. Group 0.20 highlights into three buckets:
   - timed activation / expiry
   - overlap prevention before enforcement
   - lifecycle / audit visibility
3. Add a boundary statement that says the release improves bulletin control reliability but does **not** yet complete end-to-end TSR operational behavior.
4. In QA wording, distinguish:
   - areas where confidence is strongest (dispatcher-side flows tied to completed stories)
   - areas not yet claimed (vehicle-facing propagation, trackmap, overspeed, Form A / Form B runtime)

## Screenshot pattern for TSR release notes
If screenshots are needed, ask for these first:
- timer setup in bulletin create/edit form (`StartTime` / `EndTime` visible)
- overlap warning shown during enforcement attempt
- bulletin log tab / subpage with multiple lifecycle records

If a diagram helps, use a simple Mermaid progression:
- 0.19 baseline → 0.20 landed layer → later TSR scope not yet delivered

## Pitfalls
- Do **not** imply that “TSR delivered in 0.20” means vehicle propagation, trackmap, alerting, and authorization flows are all shipped.
- Do **not** rely on live Jira links alone for final release counts; freeze the exact issue / risk set in the published note.
- Do **not** treat `WS1 / SART-1739` as 0.20 new scope; it is prior foundation.
