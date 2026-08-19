---
name: railroad-blue-signal
description: >
  Blue signal (blue flag) protection rules across GCOR, NORAC, CROR, and 49 CFR Part 218. Covers
  placement, removal, authority, on-track equipment, and special situations (rolling equipment,
  non-main track, kicking cars). Use when designing worker protection systems, blue flag enforcement
  logic, or reasoning about equipment movement in maintenance/repair contexts.
triggers:
  - blue flag / blue light / blue signal protection
  - worker protection on or near rolling equipment
  - shop track safety / equipment repair
  - on-track equipment protection
  - coupling prohibition / movement prohibition
sources:
  - 49 CFR Part 218 (FRA Blue Signal Protection)
  - GCOR 8th Edition (Apr 1, 2020), Section 5.13
  - NORAC 11th Edition (Feb 1, 2018)
  - Canadian Rail Operating Rules (CROR), Rule 26
tags: [railroad, blue-signal, worker-protection, source-skill]
audience: operator
---

# Blue Signal Protection

## When to Use
Questions about when blue signals are required, who places/removes them, what movements are prohibited, how protection works at non-main track locations, and how rules differ across GCOR / NORAC / CROR and 49 CFR Part 218. Full verbatim rule text in `references/blue-signal-rules.md`.

---

## Key Rules Index

| Rule | Ruleset | Topic |
|------|---------|-------|
| §218.21 | 49 CFR 218 | Application — when blue signal protection required |
| §218.22 | 49 CFR 218 | Blue signal equipment (flag + light) |
| §218.23 | 49 CFR 218 | Main track protection — both ends, removal authority |
| §218.25 | 49 CFR 218 | Non-main track — operating rules govern |
| §218.29 | 49 CFR 218 | Employee in charge responsibility |
| 5.13 | GCOR | Blue signal — placement, movement prohibition, removal authority |
| Rule 34 | NORAC | Working on or near tracks |
| Rule 133–135 | NORAC | Working Limits (Form D Line 4–5) — main-track equivalent |
| Rule 26(a) | CROR | Display, meaning, movement prohibition |
| Rule 26(b) | CROR | No blocking the view; relocating signals for added equipment |
| Rule 26(c) | CROR | Placement and removal — same class only |
| Rule 26(d) | CROR | Approved alternative methods |
| Rule 26(e) | CROR | Kicking protection — locked switch or derail required |

---

## Cross-Ruleset Comparison

| Attribute | 49 CFR Part 218 | GCOR 5.13 | CROR Rule 26 |
|---|---|---|---|
| Day signal | Blue flag | Blue flag | Blue flag |
| Night signal | Blue flag + blue light | Blue light only | Blue flag + blue light |
| Placement | Employee in charge | Same class of employee | Same class of workmen |
| Removal | Employee who placed it (or designated if incapacitated) | Same class who placed it | Same class only |
| Coupling/movement prohibition | Not to be coupled to or moved | Not to be coupled to, moved, or passed | Not to be coupled to or moved |
| One-end-only track variant | Not specified | N/A | Blue signal between equipment and entry switch |
| Kicking protection | Special rules per operating rules | N/A | Locked switch, or blue signal + locked derail [Rule 26(e)] |
| Manned movement exception | N/A | N/A | Notify locomotive engineer; must not move until workers clear |

---

## Key Design Implications

1. **Removal authority is strictly scoped.** Only the employee class that placed the signal can remove it. An enforcement system must track *who placed* the signal.

2. **Night visibility — GCOR vs CROR differ.** GCOR 5.13: blue light alone suffices at night. CROR Rule 26: blue *flag* and blue *light* both required. Enforcement systems must apply ruleset-specific logic.

3. **One-entry-track variant (CROR Rule 26(a)).** If a track permits entry from one end only, signal may be placed between equipment and entry switch rather than at both ends.

4. **Kicking protection (CROR Rule 26(e)).** Passive protection alone is insufficient when kicking is permitted — a physical barrier (locked switch or locked derail) is mandatory in addition to the blue signal.

5. **NORAC uses Working Limits, not blue signals, for main-track work.** Form D Line 5 is the primary NORAC mechanism. Blue flag applies to shop/facility work, not main-track MofW protection.

6. **FRA §218.23 vs. operating rules.** Federal regulation governs main track; operating rules may govern non-main track (§218.25). Systems handling both must apply the appropriate ruleset.

---

> Full verbatim rule text: `references/blue-signal-rules.md`
