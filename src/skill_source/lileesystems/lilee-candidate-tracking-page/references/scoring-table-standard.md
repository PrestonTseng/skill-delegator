# Candidate tracking scoring-table standard

Use this reference when creating or updating the canonical candidate tracking page template and layout spec.

## Current standard
- Scoring tables are for scores only.
- Do not include an in-table `Comments` row in technical/take-home scoring tables.
- Put narrative interview observations in the dedicated `Comments:` block immediately below the scoring table.
- Aggregate/category/total rows such as `A`, `B`, `C`, `D`, and `E` must be bold across the entire row, including the score cell when filled.
- Default `pending` stage tags use neutral/gray status, not yellow.
- Yellow is reserved for `Conditional` decisions, especially when a borderline candidate proceeds because the candidate pool is limited.
- Default Stage 2 interviewer is `Preston`; do not include Howard in newly created pages.

## Standard-change scope
When this standard changes, update the class-level assets for future pages:
- `templates/candidate-tracking-page-template.adf.json`
- `references/layout-spec.json`
- `scripts/verify_candidate_tracking_layout.py` if the verifier should enforce the rule
- `scripts/build_candidate_tracking_page_from_profile.py` only if generation logic is affected

Do not retrofit existing candidate pages unless Preston explicitly asks for that separate migration.
