---
name: railway-passenger-door-control
description: Research and explain responsibility boundaries for passenger train doors, platform screen doors (PSD/platform gates), control center supervision, and interlocking/CTC, then translate them into system-design guidance with exact citations.
license: Proprietary. LICENSE.txt has complete terms
---

# Railway Passenger Door / PSD Control

Use this skill when the question is not just "what does the rule say," but "who normally owns door operation in practice, how does that differ from interlocking/CTC responsibility, and what should a software system model?"

## What this skill is for
- Responsibility split between train doors, PSD/platform gates, interlocking, CBTC/ATO, OCC/CTC, and crew.
- Translating railway operating practice into product/design guidance.
- Distinguishing normal operation from override/abnormal handling.
- Answering scheduler/modeling questions such as whether a planning system should model door commands, dwell intent, platform side, or PSD requirements.

## Core rule
**Do not conflate movement authority with passenger-door authority.** Interlocking/CTC generally owns route protection and movement safety; train-side or train+station operating systems own normal door cycles.

## Working method
1. Separate the question into three layers:
   - exact regulation / standard text
   - common operating architecture in deployed systems
   - system-design recommendation for the product in front of you
2. Quote exact rule text with section numbers for regulatory claims.
3. Explicitly mark when a claim is industry pattern rather than a legal requirement.
4. Treat control-center involvement as a separate question from normal-cycle door ownership. In many systems the control center supervises, inhibits, or handles abnormal cases without being the primary normal-cycle door operator.
5. For software design, recommend modeling **service intent and dwell semantics**, not low-level door motor commands, unless the product is itself the door-control subsystem.

## Default responsibility model
### Conventional passenger rail
- Train doors: crew / operating crew responsibility.
- Door status verification before departure: crew responsibility.
- Movement interlock with doors closed: yes, often required.
- Interlocking / CTC: movement authority, route locking, conflict prevention; not normal passenger-door operation.

### Automated metro / CBTC / ATO with PSDs
- Train doors: train-side automatic logic, often under ATO/CBTC supervision.
- PSD/platform gates: station-side subsystem coordinated with train-side door logic.
- OCC/control center: supervision, remote inhibit/blocking, abnormal handling, sometimes mode management.
- Interlocking: still movement/path safety, not the business owner of passenger door cycles.

## Design translation pattern
When the product is a scheduler / mission planner / dispatch-layer system, prefer modeling:
- service type: none / board / alight / board_alight / technical_stop
- door operation required: true/false
- door side: left/right/both/auto
- PSD required: true/false/unknown
- dwell duration for passenger exchange
- optional control-mode metadata: manual_crew / train_automatic / train_plus_psd / remote_supervised

Avoid modeling the schedule primitive itself as "open door" / "close door" unless the system truly issues those physical commands.

## Pitfalls
- Do not claim that interlocking normally controls passenger doors just because route and departure are operationally linked.
- Do not treat door/PSD coordination as proof that they are one subsystem. In practice they are often distinct but interfaced.
- Do not blur normal door operation with override procedures; control-center personnel appear heavily in abnormal/override rules.
- Do not turn a dwell-time requirement into an implicit assumption that throttle/depart logic physically opens or closes doors.

## Useful supporting material
- `references/door-psd-control-citations.md` — exact FRA citations plus public industry evidence and design implications.

## Output shape
For reports or design reviews, structure the answer in this order:
1. conclusion
2. regulatory evidence
3. real-world operating patterns
4. implication for the target product/system
5. recommendation wording or data-model suggestion
