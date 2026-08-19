---
name: railroad-track-authority
description: How trains get authority to occupy main tracks — track warrants, track bulletins, track and time, Form D, mandatory directives, and dispatcher communication formats. Use when designing dispatcher interfaces, train authority workflows, or movement permit systems.
triggers:
  - designing track warrant / movement permit systems
  - dispatcher-to-train communication design
  - worksites and MofW protection
  - mandatory directive management
sources:
  - GCOR 8th Edition (Apr 1, 2020), Rules 6.11, 14.1–14.13, 15.0–15.3
  - NORAC 11th Edition (Feb 1, 2018), Rules 160–177, 400–406
  - Canadian Rail Operating Rules (CROR), January 28, 2025 Version, Rules 301–322, 849–856
---

# Track Authority — GCOR / NORAC / CROR

**Full text:** `references/gcor-twc-authority.md` · `references/gcor-track-bulletins.md` · `references/cror-track-authority.md`

## When to Use
Track warrant content/format, mandatory directives, Form D procedures, Track and Time, OCS/TOP, or dispatcher communication protocol. For NORAC Form D procedural rules see `railroad-norac-authority`. For CROR OCS/TOP rules see `railroad-cror-train-movement`.

---

## Authority Types by Ruleset

| Type | Ruleset | Issuer | Territory |
|------|---------|--------|-----------|
| Track Warrant | GCOR | Train Dispatcher | TWC-designated |
| Track Bulletin (Form A/B/C) | GCOR | Train Dispatcher | Speed/MofW restrictions |
| Track and Time | GCOR (CTC) | Control Operator | CTC territory |
| Form D | NORAC | Dispatcher | DCS-designated |
| OCS Clearance | CROR | RTC | OCS-designated |
| Track Occupancy Permit (TOP) | CROR | RTC | OCS/CTC territory |

---

## Key Rules Index

| Rule | Ruleset | Topic |
|------|---------|-------|
| 14.1–14.13 | GCOR | Track Warrant Control — limits, interpretation, overlapping warrants, Radio Blocking |
| 14.4.1 | GCOR | Radio Blocking — each train confirms position before movement |
| 15 / Form A | GCOR | Track Bulletin — speed restriction |
| 15 / Form B | GCOR | Track Bulletin — MofW Employee-in-Charge protection |
| 15 / Form C | GCOR | Track Bulletin — advisory/contractor near track; ≤20 MPH |
| 10.3 | GCOR | Track and Time (CTC) — either direction within limits; must release before time expires |
| 160 | NORAC | Form D — issued by Dispatcher; numbered from midnight; railroad letter prefix |
| 165 | NORAC | Form D dictation — digit by digit; repeat required; Time Effective only after correct repeat; must not dictate to crew on moving train |
| 172 | NORAC | Restriction within 3 miles of delivery — train must stop before delivery |
| 173 | NORAC | Form D transfer to relieving crew |
| 176 | NORAC | Form D in effect until fulfilled or cancelled; mark "X", retain 7 days |
| 177 | NORAC | Cancel protocol — both parties record; Dispatcher marks last |
| 302 | CROR | OCS Clearance — both C+LE verify possession + visually verify engine number |
| 302.2 | CROR | Superseding clearance — RTC waits for acknowledgement from both crew members |
| 302.3 | CROR | Cancellation — not effective until acknowledged |
| 303 | CROR | Max two trains same direction same limits; if comms fail → no moves except last arranged |
| 303.1 | CROR | Following train — not leave until preceding reports leaving identifiable point |
| 304 | CROR | Restricted train — must not leave until opposing train physically arrived |
| 308 | CROR | Work clearance — either direction within limits |
| 308.1 | CROR | Proceed clearance — named direction only; reverse ≤300 feet if track seen clear |

---

## Cross-Ruleset Comparison

| Attribute | GCOR Track Warrant | NORAC Form D | CROR OCS Clearance |
|-----------|-------------------|-------------|-------------------|
| Two-way movement | "WORK BETWEEN" | Line 4 (out of service) | Work Clearance (R308) |
| Following protection | Radio Blocking (R14.4.1) | R161 following instructions | R303.1 written record |
| Crew verification | Repeat word-for-word | Repeat word-for-word | Both C+LE acknowledge + visual engine# check |
| Work site protection | Form B (employee-in-charge) | Line 5 Stop Signs | TOP (R849–856) |
| Cancel protocol | Mark "VOID" | Both parties record; Dispatcher marks last | Acknowledge: number + "cancelled" + RTC initials |

---

> Full verbatim rule text: see references/ above
