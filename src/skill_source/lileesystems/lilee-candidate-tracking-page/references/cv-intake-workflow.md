# CV Intake to Candidate Tracking Page Workflow

## Why
This workflow lets Preston paste a candidate CV directly into chat, receive a grounded screening recommendation, and—only after explicit approval—turn that approved candidate into a standardized Confluence tracking page without re-entering the same information twice.

## In scope
- pasted CV text or attached resume files (PDF / DOCX)
- grounded resume screening against the live hiring plan and role JDs
- explicit manager approval gate before page creation
- structured candidate-profile JSON generation
- filled ADF generation for the canonical candidate tracking page
- preserving a reference to the original resume file in the page
- post-write layout verification

## Out of scope
- automatic page creation without Preston's approval
- creating tracking pages for every reviewed candidate by default
- changing the interview-stage structure or scoring tables
- silent format drift from the canonical baseline
- assuming a direct Confluence attachment API exists in every tool environment

## Impacted domains
- hiring review workflow
- Confluence page authoring
- resume ingestion / document extraction
- candidate comparison and screening notes
- future auditability of recruiting decisions

## Dependency assumptions
- `lilee-candidate-review` is used for the screening judgment
- `lilee-confluence-adf-authoring` is loaded before any live Confluence mutation
- `pdf` or `docx` is loaded when the source resume is a file
- `templates/candidate-tracking-page-template.adf.json` remains the canonical page body baseline
- `references/layout-spec.json` remains the canonical layout verifier input

## Recommended flow
1. Save the incoming CV text or file path under the dated `/opt/data/plans/.../` task directory.
2. Extract the resume text if the source is PDF or DOCX.
3. Review the candidate with `lilee-candidate-review` against the live hiring plan and JDs.
4. Return a concise recommendation in chat.
5. Stop unless Preston explicitly confirms the candidate should move forward.
6. Populate `templates/candidate-profile.template.json` into a real `candidate-profile.json`.
7. Run `scripts/build_candidate_tracking_page_from_profile.py` to generate a filled ADF draft.
8. Create the Confluence page from that ADF draft.
9. Attach the original resume file and update the `Resume Link` field.
10. Read back the saved page and run the layout verifier.

## Acceptance criteria
- the recommendation is grounded in current Atlassian source pages
- the candidate page is not created until Preston explicitly agrees
- the created page keeps the canonical section order and table widths
- all status-like values remain Atlassian status controls
- the page includes a usable pointer to the original resume file
- the generated page passes `scripts/verify_candidate_tracking_layout.py`

## Open questions / risks
- current tool availability may require browser/UI fallback for Confluence attachment upload
- pasted CV text may omit formatting or links present in the original file
- scanned PDFs may need OCR before a reliable screening recommendation is possible
- title markers (`O`, `X`, `?`, or none) should continue following surrounding-page convention at creation time

## Required follow-up actions
- when an actual candidate arrives, create a dated plan directory for that candidate
- save both the original source and extracted text
- capture the final `candidate-profile.json` used for page generation
- verify whether the resume file was attached successfully or is pending manual/browser upload
