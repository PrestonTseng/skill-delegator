---
name: lilee-candidate-tracking-page
description: Review approved candidate CV inputs and create or update the Lilee candidate interview tracking page in Confluence with the exact stage structure, scoring tables, status controls, and explicitly defined table/column widths.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [lilee, hiring, confluence, adf, candidate, interview]
    related_skills: [lilee-confluence-adf-authoring, lilee-candidate-review]
---

# LILEE Candidate Tracking Page

Use this skill when Preston asks you to create, duplicate, standardize, or audit the Confluence page used to track one candidate across resume review, HR screening, technical interviews, take-home assignment, and final decision.

Also use it after a resume/CV has already been screened positively and Preston wants that approved candidate turned into a new tracking page.

## What this skill owns
- the candidate-tracking page format
- the exact section order
- the scoring-table structure for each stage
- explicit table widths and explicit column widths
- status-control usage for stage/result/decision values
- the approved CV-to-page intake workflow after screening approval
- verification that a created or updated page still matches the approved layout

## Source of truth
Ground every page-format claim in these live Confluence sources:
- `2026 Candidate Overview` — pageId `3664576575` (`https://lileesystems.atlassian.net/wiki/x/PwBt2g`)
- approved blank-ish baseline used for this skill's canonical layout — pageId `3801219073`
- near-identical recent peer page for comparison — pageId `3800924168`
- completed example showing the same lifecycle filled through offer — pageId `3664543877` (`https://lileesystems.atlassian.net/wiki/x/hYBs2g`)
- hiring-process and scoring-rubric source page — `2026 Hiring Plan`, pageId `3619127299` (`https://lileesystems.atlassian.net/wiki/x/A4C31w`)

## Why this skill exists
The live candidate pages are directionally similar but not perfectly identical. Some older pages use one set of widths, and some newer pages drift by a few pixels or mix placeholder-vs-final scoring rows.

Preston explicitly asked for a **single consistent format** where:
- table width is defined explicitly
- every column width is defined explicitly
- future candidate pages stop drifting

This skill therefore standardizes on a **single canonical baseline** and provides a verifier so future edits can be checked objectively.

## Canonical baseline for new pages
Use `templates/candidate-tracking-page-template.adf.json` as the golden body for new pages.

That template is derived from the live candidate-tracking format and normalized into one reusable baseline.

Do **not** rebuild the page from scratch if you can instead patch this baseline.

## Important exception to generic Confluence house style
This page pattern intentionally follows the existing candidate pages and **does not start with a TOC**.

When using this skill for candidate pages, treat the no-TOC structure as an approved page-pattern exception. Do not inject a TOC unless Preston explicitly asks to redesign the pattern.

## Required companion skill
Before any live Confluence mutation, load:
- `lilee-confluence-adf-authoring`

Then follow this skill for the candidate-page-specific structure and width rules.

## When to create the page
Preston stated that the page is created **after the candidate passes resume review**.

Default implication:
- Stage 0 is already a pass state when creating the page
- Stage 0 summary should be populated immediately
- later stages remain pending / placeholder until those interviews happen

## CV-driven intake workflow
Use this when Preston pastes a CV directly or sends the resume file and wants a yes/no interview-worthiness recommendation before page creation.

1. Save the raw input in the current dated plan directory under `/opt/data/plans/.../`.
2. If the CV is a file, extract the text first:
   - PDF → use the `pdf` skill
   - DOCX → use the `docx` skill
3. Run the screening judgment through `lilee-candidate-review` against the live hiring plan and JDs.
4. Do **not** create the page automatically just because the model recommends moving forward.
5. Only continue once Preston explicitly agrees the candidate should move to interview tracking.
6. Build `candidate-profile.json` from `templates/candidate-profile.template.json`.
7. Generate the filled ADF page body with `scripts/build_candidate_tracking_page_from_profile.py`.
8. Create the Confluence page from that generated ADF body.
9. Attach the original resume file to the page and populate the `Resume Link` field.
   - If the current toolset does not expose a direct Confluence attachment API, use the browser/UI workflow and then read the saved page back.
10. Run the layout verifier before declaring the page complete.


## Canonical section order
Keep this exact top-level order:
1. `Candidate Info`
2. `Pipeline Overview`
3. `Stage 0 — Resume Review`
4. `Stage 1 — HR Screening Call`
5. `Stage 2 — 1st Technical Interview`
6. `Stage 3 — Take-home Assignment`
7. `Stage 4 — 2nd Technical Interview`
8. `Final Decision`

Within each stage:
- metadata table first
- scoring heading/table next when that stage has scoring
- scoring tables contain scoring rows only; do not add an in-table `Comments` row because each stage already has a dedicated `Comments:` block below the scoring table
- aggregate scoring rows (`A`, `B`, `C`, and any later category/total rows such as `D`/`E`) must be bold across the row, including the score cell when a score is entered
- `Comments:` paragraph block after the scoring table

Default pending stage tags must use a neutral/gray Atlassian status color. Reserve yellow for `Conditional` decisions so pending and conditional states are visually distinct.

Default Stage 2 interviewer is `Preston`; do not include Howard in newly created pages.

## Exact layout rule
Use the widths encoded in:
- `references/layout-spec.json`

Verify any candidate page against the same file with:
- `scripts/verify_candidate_tracking_layout.py`

If the page fails verification, do not declare the formatting complete.

## Standard-change workflow
When Preston asks to adjust the candidate-page standard itself, update the skill assets only unless he explicitly asks to retrofit existing pages.

Default standard-change scope:
1. Update `SKILL.md`, the canonical ADF template, `references/layout-spec.json`, and any verifier/builder scripts affected by the rule change.
2. Do **not** recheck every existing Confluence candidate page by default.
3. Do **not** mutate historical candidate pages by default.
4. Verify the canonical template locally and, when relevant, run the profile builder sample with `--verify` so new pages follow the new standard.
5. Report that existing pages were intentionally left unchanged and that only newly created pages will follow the new standard.

## Default workflow
1. Read the current parent page (`2026 Candidate Overview`) and confirm the destination is still correct.
2. If updating an existing candidate page, read the page as ADF first.
3. If creating a page from an approved CV, first generate the candidate profile JSON and filled ADF draft instead of editing the raw template by hand.
4. Start from `templates/candidate-tracking-page-template.adf.json` instead of hand-authoring tables.
5. Replace placeholders with candidate-specific values.
6. Keep status-like values as ADF `status` nodes, not plain text.
7. Create or update the page in ADF.
8. If a resume file exists, make sure the page keeps a pointer to the original file in `Resume Link`.
9. Read the saved page back.
10. Run `python scripts/verify_candidate_tracking_layout.py --page-id <id>` or validate the local ADF file before write-back.
11. Only report success after the verifier passes or after any intentional exception is explicitly called out.

## Title guidance
The live parent page uses titles of the form:
- `2026 - <Honorific> <Candidate Name> - <Applied Position> - Stage <N> <marker>`

Examples in the overview children include markers such as `O`, `X`, `?`, or no marker depending on pipeline state.

Do not invent a new title convention without checking the surrounding candidate pages first.

## Stage update workflow
When Preston asks to fill a completed interview stage on an existing candidate page:

1. Read the live candidate page in ADF first.
2. Patch only the target stage's heading status, metadata table, scoring values, and comments block.
3. Keep comments concise and decision-focused; write narrative observations in the dedicated `Comments:` block below the scoring table, not as an in-table scoring row.
4. Scoring tables should contain only scored criteria and aggregate/total rows; do not reintroduce a `Comments` row inside the scoring table.
5. When filling aggregate/category/total scores, keep the entire aggregate row bold, including the score cell.
6. If the decision is borderline but Preston wants to proceed because the candidate pool is limited, use a yellow Atlassian status labeled `Conditional` rather than `PASS` or `Reject`.
7. Put the candidate-pool reason directly in the stage comments so the result is auditable.
8. If Preston asks about AI-collaboration maturity, record the concrete tooling level in comments; for example, distinguish simple chat / VS Code extension use from skill- or MCP-based workflows.
9. Read back the saved page and run `scripts/verify_candidate_tracking_layout.py --page-id <id>` before reporting success.

See `references/stage-2-conditional-take-home-update.md` for the Stage 2 conditional take-home pattern and example wording.

## Files bundled with this skill
- `templates/candidate-tracking-page-template.adf.json` — canonical reusable ADF body with placeholders
- `templates/candidate-profile.template.json` — input schema/example for approved-CV page creation
- `references/layout-spec.json` — exact section/table/column spec
- `references/source-pages.md` — page IDs and rationale for the chosen baseline
- `references/layout-drift-summary.md` — observed live drift across 2026 candidate pages
- `references/cv-intake-workflow.md` — end-to-end workflow from CV intake to page creation
- `references/stage-2-conditional-take-home-update.md` — pattern for borderline Stage 2 updates where take-home proceeds conditionally due to candidate-pool scarcity
- `references/scoring-table-standard.md` — current scoring-table conventions: no in-table comment rows, bold aggregate rows including score cells, neutral pending tags, yellow conditional tags, and default Stage 2 interviewer ownership
- `scripts/build_candidate_tracking_page_from_profile.py` — fills the canonical template from a structured candidate profile JSON
- `scripts/verify_candidate_tracking_layout.py` — structural verifier for widths/order/row labels

## Pitfalls
- Do not create this page in Markdown or HTML first and "convert later".
- Do not let Confluence auto-resize tables without checking the saved ADF.
- Do not mix the older wide-table widths and the newer placeholder-table widths on the same page.
- Do not add arbitrary scoring rows; the canonical scoring tables intentionally exclude in-table `Comments` rows because each stage has a dedicated `Comments:` block below the table.
- Do not replace status controls with plain text like `PASS`, `Reject`, or `pending`.
- Do not create the page before Preston explicitly agrees the candidate should move forward.
- Do not drop the original resume file; keep the file itself plus extracted text in the plan directory so the page can be audited later.
- Do not inject a TOC into this page pattern unless Preston explicitly requests a redesign.

## Completion standard
A candidate page task is only done when you can state:
- which parent page was used
- whether the task was create vs update
- which baseline/template file was used
- whether the saved page matched `layout-spec.json`
- whether all stage/decision states remained status controls
- where the extracted resume text was saved
- whether the original resume file was attached to the page or is still pending manual/browser upload
- any intentional deviations from the canonical candidate-page layout
