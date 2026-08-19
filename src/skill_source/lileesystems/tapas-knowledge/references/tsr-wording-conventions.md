# TSR / Bulletin Diagram Wording Conventions

Use these wording choices consistently in TAPAS / SafeART TSR diagrams and backlog artifacts when describing TSR, Form A, and Form B behavior.

## Diagram discipline

- **Do not introduce inferred workflow labels as if they were source text.** If a step name is not explicitly grounded in the backlog/spec, either:
  - use the source wording directly, or
  - stop and confirm the proposed summary wording with Preston before putting it on the diagram.
- Prefer **source-faithful operational verbs** over convenience summaries like `publish initial mission impact`, `publish ... update`, `normal runtime status`, or other packaging phrases that collapse multiple requirements into one invented step.
- For cross-team diagram readability, `JPS -> GUI` can stay **generic at the transport level**, but it should still show the two read/update triggers when relevant:
  - `HTTP GET`
  - `WebSocket bulletin change event`
- Treat **speed limit** as a field on every bulletin family in diagrams; for **Form A**, call out that the value is **forced to 0** instead of implying the field does not exist.
- When the user wants dispatcher-operational explanation rather than pure backend flow, include a separate **GUI operation flow** diagram instead of overloading runtime diagrams with editing-policy commentary.

## Approved phrasing

### Shared command wording

- **Enforcement OFF command:** `Disable bulletin enforcement`
  - Prefer this over `Revoke bulletin` when the bulletin record still exists and only enforcement is being turned off.

### Form A

- **Boundary-hold MA update:** `Reset authorized milepost range to end at Form A boundary`
  - Do **not** append `(FromMP)` in the visible label when this wording is used.

### Form B

- **Boundary-hold MA update:** `Reset authorized milepost range to end at Form B boundary`
  - Mirror the Form A sentence shape; swap only the bulletin type.
- **Approved transit update:** `Extend MA through Form B zone at restricted speed`
  - Prefer this over longer variants like `Rebuild MA with Form B speed limit through zone`.
- **Hold-state wording:** `Vehicle holds at Form B boundary ...`
  - Name the boundary explicitly instead of generic `holds at boundary`.

### Generic TSR

- **Zone transit update:** `Extend MA through TSR zone with speed limit applied`
- **In-zone speed refresh:** `Update MA to apply TSR speed limit through current zone`
  - Use this when the vehicle is already inside the TSR zone when the bulletin becomes Effective.

## Family rule

When the three bulletin diagrams are shown side-by-side, keep the verb pattern aligned wherever the semantic shape is parallel:

- `Reset authorized milepost range ...` = no-entry / boundary-hold effect
- `Extend MA through ...` = allowed transit through the affected zone
- `Update MA to apply ...` = in-zone refresh while authority remains continuous
- `Disable bulletin enforcement` = enforcement toggled OFF without deleting the bulletin record

## Mermaid authoring pitfall

When a Mermaid node label must show a literal bracketed status like `[IN ZONE]`, quote the full label text instead of placing raw square brackets inside a `[...]` node definition.

- Preferred: `C2["SS creates high-priority [IN ZONE] Pending request"]`
- Avoid: `C2[SS creates high-priority [IN ZONE] Pending request]`

Reason: Mermaid parses `[` and `]` as node-shape delimiters, so unquoted bracketed status text inside a square-node label can trigger a parse error.

## Why this matters

These phrases were reviewed and accepted during the sequence-diagram wording cleanup across Form A, Form B, and generic TSR. They keep the diagram language aligned with the actual operator/system action:

- boundary-hold text describes the MA consequence without extra parenthetical noise
- approved-transit text distinguishes `allowed to pass` from generic MA rebuild wording
- in-zone refresh text makes clear that TSR changes speed authority, not zone entry permission
- enforcement-off text describes a state change, not bulletin deletion
