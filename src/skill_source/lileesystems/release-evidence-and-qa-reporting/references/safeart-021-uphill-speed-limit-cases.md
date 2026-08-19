# SafeART 0.21 Uphill speed-limit advisory cases

Use this note only as a concrete example of the class-level targeted-qualification workflow. Re-fetch the live source before future publication because the catalog may advance.

## Provenance

- Authoritative case catalog: Confluence `Uphill Test Cases`, page `3524067749`.
- Source version used: v51, published 2026-08-05.
- Cases added by Lorenzo: S31.8, S31.9, S32.2.
- Execution result: Preston confirmed immediately after authoring that all three had just been tested and passed.
- Release artifact destination: `2.5.1.1. Release-specific Uphill Cases` in the SafeART 0.21 release note.

## Case definitions

### S31.8 — Bulletin Creation

- Scenario: create a signal-based TSR with speed 50, start 11L, end 15L, scheduled time range.
- Expected advisory identifies: `W3T`, `C3T_1`, `C3T_2`, `H3T`, `C5T_1`, `C5T_2`.
- Semantics: warning is non-blocking; creation remains allowed and signal-derived mileposts remain visible.
- Result confirmed: PASS.

### S31.9 — Bulletin Creation

- Scenario: create an upward milepost TSR with speed 50, start 1k200, end 1k800, scheduled time range.
- Expected advisory identifies: `W1T`, `W2T`, `W3T`.
- Semantics: warning is non-blocking; creation remains allowed with entered mileposts.
- Result confirmed: PASS.

### S32.2 — Bulletin Update

- Scenario: edit an existing TSR from speed 20 to 50 and range 1k200–1k800 to 2k200–2k800.
- Expected advisory identifies: `W4T`, `W5T`, `W6T`.
- Semantics: warning is non-blocking; updated speed/range save and edit time differs from creation time.
- Result confirmed: PASS.

## Reconciliation outcome

- Detailed Uphill rows: 4 → 7.
- Detailed native PASS controls: 7.
- Overview: `UPHILL — 7 / 7 PASS`.
- Section summary: `7 New / Updated Test Cases • 7 PASSED`.
- Coverage line: `Speed-limit advisory validation: S31.8, S31.9, S32.2`.

## Source-quality note

The source S31.8 expected-result text included an apparent copied bulletin-type phrase inconsistent with its TSR `Given`. The release artifact retained the uncontested advisory tracks, non-blocking behavior, and signal-derived mileposts rather than publishing the contradictory copied type label.
