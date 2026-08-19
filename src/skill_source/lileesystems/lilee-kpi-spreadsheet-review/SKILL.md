---
name: lilee-kpi-spreadsheet-review
description: >
  Review and refine LILEE employee KPI Excel workbooks, especially H1/H2 SafeART/TAPAS KPI tables. Use when Preston asks to review KPI items, make descriptions more precise or measurable, align KPI commitments with Delivery Maps/specs, or return an edited .xlsx while preserving the corporate template.
---

# LILEE KPI Spreadsheet Review

Use this skill together with the general `xlsx` skill. This skill governs LILEE-specific source alignment, wording, scope judgment, and review output; `xlsx` governs workbook mechanics.

## Objective

Turn broad KPI labels into manager-reviewable commitments without inventing scope, dates, owners, targets, or implementation promises. Preserve the workbook's established structure and return a verified `.xlsx` artifact.

## Required source hierarchy

For each KPI feature area:

1. Read the live Delivery Map linked from the KPI row.
2. Read the linked spec/backlog when behavioral or authority boundaries matter.
3. For ongoing architecture work, inspect current redesign artifacts and keep unapproved conclusions labeled as study/design/candidate outputs.
4. Treat the spreadsheet wording as the commitment under review, not automatically as current source of truth.

If the spreadsheet promises implementation, rollout, replacement, or “solve all issues,” but the live plan still gates implementation behind study, RCA, constraints, architecture, or spec approval, rewrite the KPI to the latest reviewable gate. Make the material scope correction explicit in review notes.

## KPI eligibility gate

Before making an item precise, decide whether it deserves KPI weight at all:

1. **Routine/already committed delivery:** treat as baseline job expectation, not a separate KPI merely because it appears in a release plan.
2. **Technical Lead leverage:** suitable when it transfers ownership, develops a stack owner, creates predictable delivery, or lets execution be delegated.
3. **Strategic study/design:** suitable only when it names a final maturity and evidence-based outcome.
4. **Operational improvement:** suitable when it changes a measurable system/process outcome, not when it only produces a document.

A committed feature may be evidence for a leadership KPI (for example, release governance or ownership transfer) without being a standalone KPI item.

When manager feedback changes the KPI model from feature delivery to role impact, stop editing the workbook. Discuss and confirm the new objective structure, weights, maturity boundaries, and acceptance evidence first. If the user says “discuss here” or “do not edit Excel,” record the proposal separately and do not touch the workbook until a later explicit request.

Read `references/tech-lead-outcome-kpi-design.md` for ownership-transfer, release-outcome, strategic-study, and two-audience-documentation patterns.

## Preferred KPI item shape

Write weighted items as:

`<number> <action> + <bounded scope> + <verifiable output / done condition>`

A strong description identifies enough of these to support objective evaluation:

- artifact or capability produced;
- service/system boundary;
- included behavior;
- review or verification environment;
- authority boundary where confusion is likely.

Avoid vague standalone phrasing such as:

- `study and improve`;
- `design a completed architecture`;
- `make an implementation plan`;
- `make sure all known issues are solved`;
- a feature noun with no done condition.

Prefer concise completion language such as:

- `Publish a reviewable target architecture covering service boundaries, module responsibilities, major data flows, and unresolved ADRs; complete PO review.`
- `Provide bounded historical queries with topic/payload filtering, pagination, raw inspection, and selected ICD-aware display.`
- `Produce and review a shared-resource-safe redesign logic model covering acquisition, hold, transfer, release, occupancy, and defensive checks.`

## Review workflow

1. Inspect all workbook sheets, formulas, merged ranges, links, styles, row heights, and weighted items.
2. Identify the active KPI sheet and list every non-empty objective/task row.
3. Classify each candidate as routine delivery, role-leverage outcome, strategic study, or operational improvement. Remove/reframe routine items before polishing wording.
4. If the KPI philosophy, role model, or weights are changing, run a discussion-only design pass and obtain explicit approval before workbook edits.
5. Confirm item scope against live linked sources before rewriting.
6. For each study, name its final maturity (`design-complete`, `design + migration plan`, or `implementation-verified`) and the evidence that proves it.
7. Rewrite headings only when doing so improves scope orientation; rewrite weighted task rows for action, boundary, and verifiability.
8. Correct obvious spelling and numbering problems.
9. Preserve dates, weights, links, formulas, merged cells, and styles unless the user explicitly asks to change them.
10. If longer text needs more room, preserve wrapping and adjust only affected row heights.
11. Verify workbook integrity and deliver both the revised workbook and concise review notes.

## Workbook editing safety

Corporate KPI workbooks can contain Excel extension namespaces that generic XML serializers do not preserve safely.

- Do **not** parse and reserialize a worksheet with Python `xml.etree.ElementTree` merely to change cell text. It can rename/remove namespace declarations while leaving `mc:Ignorable` prefixes unchanged, producing a workbook that libraries can read but desktop Excel reports as corrupt.
- For text-only changes where each shared-string entry is unique, prefer copying the original ZIP package and replacing only the target entries in `xl/sharedStrings.xml`; preserve all worksheet bytes.
- If row/cell structure must change, use an OOXML-aware workbook writer or targeted raw-byte edits that preserve the worksheet root and namespace declarations. Rebuild from the original or last independently verified workbook, never from a damaged derivative.
- Give repaired outputs a new versioned filename so users do not reopen a cached bad attachment.
- Run `scripts/validate_ooxml_namespaces.py <workbook.xlsx>` before delivery. It checks ZIP CRC, parses all XML/RELS parts, and detects `mc:Ignorable` prefixes that are not declared on the worksheet root.
- Also open the file with two independent readers when practical (for example OpenPyXL and Calamine). A single library successfully reading the workbook is insufficient evidence that desktop Excel will accept it.

## Verification requirements

- Weighted items still total 100% unless the source workbook intentionally uses another total.
- No unexpected value, formula, style, merge, or link changes.
- Scan the whole workbook for formula errors, including archived sheets.
- Repair an unrelated pre-existing formula error only when the intended reference is directly confirmed by adjacent formulas or a parallel version of the same sheet; disclose the repair.
- Re-open the saved workbook and confirm all rewritten cells read back correctly.
- When formulas exist, follow the general `xlsx` recalculation/error-check workflow where available. Do not claim recalculation if only structural read-back was performed.

## Output

When the user requests discussion/review before editing:

- present the proposed KPI architecture, weights, maturity boundaries, and evidence;
- resolve one material decision at a time;
- keep a reviewable proposal outside the workbook;
- explicitly confirm that Excel remains unchanged.

Only after workbook editing is explicitly authorized, deliver:

- revised `.xlsx`;
- concise review notes describing material wording/scope corrections;
- verification summary: item count, weight total, formula-error status, namespace/package validation, independent-reader status, and any disclosed repair.

Do not flood the user with a cell-by-cell diff unless requested.

## TAPAS/SafeART boundary reference

Read `references/tapas-kpi-boundary-checks.md` when KPI items cover TSR/Form A/Form B, Seshat, route ordering, WSS/PLC redesign, or next-generation TAPAS architecture.
