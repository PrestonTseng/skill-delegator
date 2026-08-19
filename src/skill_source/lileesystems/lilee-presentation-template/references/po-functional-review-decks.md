# PO Functional-Review Deck Pattern

Use this pattern when the user wants a PO-facing review deck for system behavior, functional architecture, or data flow.

## Goal
Help the PO understand **how the system runs** in nominal and special-case flows without dropping to full implementation sequence detail.

## Recommended slide families
1. **Boundary / reading guide**
   - optional and very light
   - define source of truth and what each diagram element means

2. **Shared nominal operation**
   - usually best as a simplified sequence diagram
   - keep only the major systems and the authoritative writes / handoffs

3. **Per-scenario happy paths**
   - one slide per scenario / restriction family
   - embed small notes for golden copy, writer role, and minimum schema/object identity

4. **Validation / branching / exception slides**
   - use branch diagrams when the point is a rule split
   - use side-by-side compare when the same trigger causes different outcomes

5. **Operational surfaces**
   - use a fan-out map for visibility, logging, ACK, alerting, and subscriber surfaces

## Diagram-form heuristic
- **Sequence**: ordering, authority handoff, state write, approval flow
- **Compare**: same trigger, different behavior across cases
- **Branch**: blocking vs advisory, valid vs invalid, approve vs pending vs void
- **Fan-out**: one source driving multiple UI / persistence / alert surfaces

## What to preserve from source material
Do not simplify away:
- golden copy / operational truth location
- operational writer vs forwarder vs history persister
- authoritative data flow across major systems
- key object identities and lifecycle markers

## What to drop from presentation diagrams
Usually remove:
- DTO / payload detail
- internal service/class decomposition unless explicitly required
- message-by-message chatter
- low-value acknowledgements that do not change the story
- engineering decomposition into tickets / workstreams

## Session-specific lesson captured
In one TSR system-operation review, the useful correction was:
- embed architecture, golden-copy, writer-model, and schema notes directly into the main diagrams
- avoid separate theory slides when those concepts mainly exist to explain the operational flows
- keep subsystem decomposition collapsed to the product-relevant boundary when internal boxes hurt readability
