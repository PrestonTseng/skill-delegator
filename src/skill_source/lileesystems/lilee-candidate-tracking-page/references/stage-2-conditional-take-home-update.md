# Stage 2 conditional take-home update pattern

Use this reference when updating an existing candidate tracking page after a 1st technical interview where the interview result is borderline but the team wants to move to take-home because the candidate pool is limited.

## Recommended result/status
- Use an Atlassian status node, not plain text.
- Preferred label: `Conditional`
- Preferred color: yellow
- Apply it consistently to:
  - the `Stage 2 — 1st Technical Interview` heading status
  - the Stage 2 metadata table `Result` field

## Scoring pattern
When the interview is weaker than the resume but not a hard reject, fill the Stage 2 scoring table rather than leaving it blank.

Keep the scoring table focused on scores only:
- do not add or preserve an in-table `Comments` row;
- put narrative rationale in the dedicated `Comments:` block below the table;
- keep aggregate rows (`A`, `B`, `C`/`Total`) bold across the row, including the score cell.

Example scoring from the 2026-07-02 update, adapted to the current no-in-table-comments standard:
- `Technical Presentation` aggregate: `2.4`
- `Communication clarity`: `2.5`
- `Depth of representative project walkthrough`: `2.0`
- `Relevance of experience`: `3.0`
- `Problem-solving approach`: `2.0`
- `Soft Skills` aggregate: `2.7`
- `Presentation structure and delivery`: `2.5`
- `Communication and articulation`: `2.5`
- `Learning agility and growth mindset`: `3.0`
- `Total`: `2.6`

## Concise comments pattern
Keep comments short and decision-focused. Include:
- what the interview failed to validate,
- the most important technical concern,
- the AI-collaboration observation if Preston asked about it,
- the decision rationale if candidate-pool scarcity changes the outcome.

Example:
- Resume relevance remains high, but Stage 2 did not validate the same system-architecture depth.
- NODE.X walkthrough lacked clear Server/Agent/Frontend/DB/Grafana boundaries; candidate could not reason from 10–100 devices to 1,000 devices.
- Ramp-up plan was generic. AI collaboration is currently limited to chat and VS Code extensions (Codex/Claude Code); no skill/MCP-style workflow.
- Decision: Conditional proceed to take-home because the current candidate pool is limited; use the assignment to verify coding execution, tests, and architecture/trade-off explanation.

## ADF mutation workflow
For a small Stage 2 update:
1. Read the live page in ADF first.
2. Patch only the Stage 2 heading, Stage 2 metadata table, Stage 2 scoring table, and Stage 2 comments paragraph/list.
3. Preserve all other nodes exactly.
4. If using direct Confluence REST because the MCP update payload is large, use the v2 pages endpoint with `body.representation = atlas_doc_format`, increment the page version, and perform a live-body drift guard immediately before PUT.
5. Read back the page and verify:
   - Stage 2 heading/status persisted as `Conditional` yellow status.
   - Stage 2 metadata `Result` persisted as `Conditional` yellow status.
   - Total score and comments persisted.
   - The scoring table has no in-table `Comments` row.
   - `verify_candidate_tracking_layout.py --page-id <pageId>` still passes.
