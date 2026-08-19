---
name: railroad-signal-aspects
description: >
  North American railroad signal indication system — NORAC, GCOR, and CROR signal aspect names,
  required actions, speed regimes, cab signal conformity rules. Use when designing signal-related
  features or reasoning about train movement authority via signals.
triggers:
  - designing signal display or enforcement logic
  - asking what a signal aspect means
  - cab signal / fixed signal conformity
  - PTC signal enforcement
sources:
  - NORAC 11th Edition (Feb 1, 2018)
  - GCOR 8th Edition (Apr 1, 2020)
  - Canadian Rail Operating Rules (CROR), January 28, 2025 Version
---

# Signal Aspects — NORAC / GCOR / CROR

**Full text:** `references/norac-signal-aspects-rules.md` · `references/gcor-signal-rules.md` · `references/cror-signal-aspects.md`

## When to Use
Signal aspect names, required actions, speed regimes, cab signal conformity, or design implications for signal enforcement logic.

---

## Speed Definitions

| | NORAC | CROR |
|---|---|---|
| Limited | ≤45 MPH | ≤45 MPH |
| Medium | ≤30 MPH | ≤30 MPH |
| Reduced | — | ≤25 MPH |
| Slow | ≤15 MPH | ≤15 MPH |
| Diverging | — | ≤15 MPH through turnouts |
| Restricted | ≤20 MPH; stop within ½ visible distance of train/obstruction/Stop | ≤15 MPH; stop within ½ range of vision; stop short of train/obstruction/misaligned switch |

---

## NORAC Key Aspects (Rules 280a–292)

| Rule | Name | Key Action |
|------|------|-----------|
| 281 | CLEAR | Normal Speed |
| 281a | CAB SPEED | Per cab signal; ≤60 MPH if no cab signal |
| 281b | APPROACH LIMITED | Approach next at Limited |
| 281c | LIMITED CLEAR | Limited through switches, then Normal |
| 282 | APPROACH MEDIUM | Approach next at Medium |
| 282a | ADVANCE APPROACH | Stop at 2nd signal; reduce to Limited when engine passes |
| 283 | MEDIUM CLEAR | Medium through switches, then Normal |
| 285 | APPROACH | Stop at next; reduce to Medium when engine passes |
| 286a | LIMITED APPROACH | Stop at next; Limited through switches then Medium |
| 287 | SLOW CLEAR | Slow through switches, then Normal |
| 290 | RESTRICTING | Restricted Speed until whole train clears switches AND past more favorable signal |
| 291 | STOP AND PROCEED | Stop first, then same as Restricting |
| 292 | STOP SIGNAL | Stop |
| 280a | CLEAR TO NEXT INTERLOCKING | ≤79 MPH; approach next home signal prepared to stop |

Full 29-aspect table → `references/norac-signal-aspects-rules.md`

---

## NORAC Cab Signal Conformity (Rule 279)

| Fixed Signal | Conforming Cab Signal |
|-------------|----------------------|
| Clear | Clear |
| Cab Speed | Clear / Cab Speed / Approach Limited / Approach Medium |
| Medium Clear | Approach Medium |
| Approach | Approach |
| Restricting | Restricting |
| Stop and Proceed | Restricting |

Cab signal governs when: (1) CSS without fixed ABS [R562], (2) cab changes between fixed signals [R553], (3) cab more restrictive on block entry [R552].

---

## CROR Key Aspects (Rules 405–440)

Compound naming pattern: **[speed at signal/turnout] TO [next block speed]**

| Rule | Name | Key Action |
|------|------|-----------|
| 405 | CLEAR | Proceed |
| 406–409 | CLEAR TO [LIMITED/MEDIUM/DIVERGING/SLOW] | Proceed; approach next at named speed |
| 411 | CLEAR TO STOP | Proceed; prepared to stop at next signal |
| 412–415 | ADVANCE CLEAR TO [speed] | Proceed; approach **second** signal at named speed |
| 416–421 | LIMITED TO [CLEAR/…/STOP] | Limited at signal/turnouts; next block at named speed |
| 422–427 | MEDIUM TO [CLEAR/…/STOP] | Medium at signal/turnouts |
| 428–430 | DIVERGING TO [CLEAR/STOP] / DIVERGING | Diverging at signal/turnouts |
| 431–435 | SLOW TO [CLEAR/…/STOP] | Slow at signal/turnouts |
| 432A/433A/434A | DIVERGING TO [LIMITED/MEDIUM/DIVERGING] | Verified in PDF |
| 436 | RESTRICTING | Restricted Speed |
| 437 | STOP AND PROCEED | Stop, then Restricted Speed |
| 439 | STOP | Stop |
| 440 | DIRECTION INDICATOR | Flashing arrow — route lined in indicated direction |

Full table → `references/cror-signal-aspects.md`

---

## GCOR Signal Principles (Section 5)

- Any object waved violently by any person = **STOP** [GCOR 5.3.4]
- Improperly displayed/absent signal → most restrictive indication [GCOR 5.15]
- Blue signal: must not couple to, move, or pass [GCOR 5.13] → see `railroad-blue-signal`

Full GCOR Section 5 → `references/gcor-signal-rules.md`

---

## Key Design Implications

1. **Cab signal more restrictive than fixed on block entry → cab signal governs** [R552].
2. **Speed reduction trigger differs by aspect:** Approach/Approach Slow → reduce when engine *passes* signal. Medium/Limited/Advance Approach → reduce when signal is *clearly visible*.
3. **Restricted Speed is conditional:** ≤20 MPH AND stop within ½ range of vision AND stop short of any obstruction/Stop signal.
4. **Stop and Proceed (291) vs. Restricting (290):** Identical clearing conditions; Stop and Proceed requires a full stop *before* proceeding.
5. **CROR compound naming:** First term = speed at signal/turnout; second term = approach speed for next signal.
