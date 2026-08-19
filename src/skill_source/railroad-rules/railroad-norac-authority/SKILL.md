---
name: railroad-norac-authority
description: >
  Source skill for NORAC Operating Rules 11th Edition — Movement Permit Form D (Rules 160–177)
  and Form D Control System / DCS (Rules 400–406). For general movement rules see
  `railroad-norac-train-movement`. For signal rules see `railroad-norac-signals`.
sources:
  - "NORAC Operating Rules, 11th Edition (February 1, 2018)"
tags: [railroad, NORAC, Form-D, DCS, track-authority, source-skill]
audience: operator
---

# NORAC — Form D Authority and DCS (Rules 160–177, 400–406)

## When to Use
Questions about issuing, delivering, canceling, or complying with NORAC Form D track authority,
or DCS territory occupancy rules. Full rule text in `references/norac-authority.md`.

---

## Form D Lines Reference

| Line | Purpose |
|------|---------|
| 1 | Speed restriction |
| 2 | Authority to occupy DCS territory (direction or both) |
| 4 | Remove track from service (out-of-service limits) |
| 5 | Working limits (with stop signs) |
| 6 | Substitute non-signaled DCS for ABS failure |
| 7 | Remove interlocking or controlled point from service |
| 8 | Prepare disabled train for assist |
| 9 | Authorize assisting movement |
| 10 | Notify of TBS in service |
| 12 | Notify of malfunctioning crossing warning |
| 13 | General instructions / special orders |

---

## Form D Administration Key Points (Rules 160–177)

- **160:** Issued by Dispatcher only; numbered consecutively from midnight; prefixed by railroad code.
- **161:** Legible, no erasure; applicable line numbers circled; employees review entire form.
- **165 — Dictation:** Digit by digit for all numerals. All addressees repeat in order. Dispatcher must not give "Time Effective" until all addressees repeat correctly.
- **165 — Electronic:** Receiving employees verify number and date of each Form D received.
- **167:** If communication fails before Time Effective — train must not proceed.
- **168:** Error before Time Effective → void and reissue. Error after Time Effective → cancel.
- **170:** Dispatcher applies blocking devices at interlocking/CP to prevent departure without Form D.
- **171:** Train must not exceed **30 MPH** while awaiting delivery on the fly.
- **172:** Restriction within **3 miles** of delivery point → train must stop.
- **173:** All in-effect Form D's delivered to relieving crew; copies compared.
- **176:** In effect until fulfilled or canceled. Mark "X" and retain **7 days**.
- **177 — Cancel:** Both parties record Form D number, date, and cancellation info. Dispatcher must not mark own copy until all addressees canceled.

---

## DCS Key Rules (Rules 400–406)

- **400:** Form D line 2 required for all movement outside yard limits. Overlapping opposing authorities must never be issued. Before issuing in non-signaled DCS: Dispatcher confirms track clear.
- **400 — Limits ending at station:** Authority ends at home/CP signal (interlocking), specified point (passenger station), or fouling point of first hand-operated switch.
- **401:** Non-signaled DCS speed: passenger ≤59 MPH, freight ≤49 MPH. Approach home/CP signals prepared to stop.
- **402 — Reverse movement options (non-signaled):** (1) new Form D line 2; (2) verbal permission + crew on leading end + Restricted Speed; (3) crew precedes + Restricted Speed + ≤last whole milepost/station; (4) revert to ABS if against current (Form D line 2 canceled first).
- **403:** Both-directions line 2 = exclusive occupancy; Dispatcher may not authorize other movements.
- **405:** Train must report to Dispatcher upon entering and clearing DCS territory. Panel board indication lights must NOT be used to confirm track clear.
- **406 — ABS substitution:** Before issuing line 6, all entrance signals at Stop + blocking devices applied. ABS and CSS rules do not apply while non-signaled DCS is in effect.
