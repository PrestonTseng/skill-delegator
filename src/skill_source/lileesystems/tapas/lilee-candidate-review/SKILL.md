---
name: lilee-candidate-review
description: Review incoming LILEE candidate resumes against the current hiring plan and role JDs, produce a concise recommendation, and optionally prepare candidate tracking pages.
---

# LILEE Candidate Resume Review

Use this skill when Preston asks to review a new candidate resume, compare multiple resumes, rank candidates for a role, or continue a prior hiring-review workflow.

## What this skill is for
- Resume screening for LILEE hiring
- Reviewing either pasted CV text or attached resume files
- Comparing candidates against the active Full Stack / Backend hiring bar
- Producing a concise manager-facing recommendation in chat
- Preparing approved candidates for Confluence tracking-page creation

## Required grounding
Always ground the review in Atlassian source material before making fit claims.

Primary source-of-truth pages:
- `2026 Hiring Plan` — pageId `3619127299`
- `Job Description - Full Stack Engineer` — pageId `3618635786`
- `Job Description - Backend Engineer` — pageId `3618897936`
- `2026 Candidate Overview` — pageId `3664576575`

If the hiring cycle changes, re-read the current source pages instead of assuming these remain valid forever.

## Default workflow
1. **Recover prior context first**
   - Check `/opt/data/plans/` for the latest candidate-review directory.
   - Read prior notes/rankings before reviewing the new resume so the recommendation stays calibrated to the same batch.
   - Create a new dated plan directory for the current candidate and write `status.md` + `notes.md` early.

2. **Read the source of truth from Confluence**
   - Pull the hiring plan and role JD pages directly through Atlassian MCP.
   - Do not rely on memory or old summaries alone.

3. **Extract the resume text**
   - If Preston pasted the CV directly in chat, save the raw text into the current plan directory under `raw/` before analyzing it.
   - If a PDF arrives, load the `pdf` skill and extract the text into the current plan directory under `extracted/`.
   - If a DOCX arrives, load the `docx` skill and extract the text into the current plan directory under `extracted/`.
   - Keep both the original file path and the extracted text file so later ranking, page creation, or audit work can reuse them.

4. **Identify the applied role and candidate facts**
   - Capture: applied role, education, stated years of experience, recent employer, availability, language ability, work authorization notes, and any explicit links/portfolio references.
   - Note inconsistencies explicitly (for example, stated total years not matching the listed job history).

5. **Compare against the JD in two layers**
   - **Direct evidence:** technologies and work patterns explicitly demonstrated in job-history bullets.
   - **Weak evidence / claimed only:** items present only in skill lists, summaries, or self-description.
   - Separate these clearly; do not over-credit keyword-only claims.

6. **Produce a decision-oriented recommendation**
   Use one of these default outputs:
   - `Strong yes for interview`
   - `Yes for interview`
   - `Conditional yes / medium priority`
   - `Conditional yes / lower-priority HR screen`
   - `Do not prioritize / likely pass`

7. **Rank relative to the active batch when relevant**
   - If prior candidates were already reviewed, place the new candidate into the current ordering rather than judging them in isolation.
   - Explain the main comparison axis (stack fit, domain overlap, backend depth, communication risk, ramp time, etc.).

8. **Decide whether to create a Confluence candidate page**
   - Default: create candidate tracking pages for clear shortlist / clear pass-to-next-stage candidates.
   - Even for strong candidates, do **not** create the page until Preston explicitly confirms to move forward.
   - Once Preston approves, hand off to `lilee-candidate-tracking-page` and build the page from the approved CV plus the original resume file path.
   - If the candidate is only conditional or lower-priority, do **not** create the page by default; mention that it was intentionally skipped unless Preston asks for it anyway.

## Review structure to use in chat
Prefer this concise structure:
- **Conclusion first**
- **Why the candidate is worth considering**
- **Why the candidate is not top-priority / main gaps**
- **Specific interview focus if moved forward**
- **Relative ranking vs prior batch**

Keep the answer crisp and decision-oriented; do not dump the whole resume back to Preston.

## Evaluation heuristics
### Strong positive signals
- Recent production experience directly matching the role JD
- Clear backend ownership, frontend ownership, or both
- Evidence of testing discipline, deployment, troubleshooting, and cross-module/system work
- Domain adjacency to monitoring, control, real-time systems, IoT, or industrial software
- Concrete shipped features rather than generic skill lists

### Risk signals
- Key JD items missing from work-history bullets and present only in skill keywords
- Role mismatch (e.g. desktop/device/tooling profile for a web full-stack opening)
- Heavy ramp-up required into Python/FastAPI/PostgreSQL/GraphQL/Docker/Linux/testing stack
- Communication constraints likely to affect the actual team workflow
- Work-history or availability inconsistencies that require HR clarification

## Confluence candidate page pattern
When creating a candidate page under `2026 Candidate Overview`:
- Reuse the existing candidate page structure already in the space.
- Populate Stage 0 / Resume Review with a concise summary and recommended HR-screen focus.
- Leave later stages templated unless actual interview data exists.

See `references/confluence-page-pattern.md` for the observed shortlist-page pattern and the default rule on when to create those pages.

## Pitfalls
- Do not score a candidate purely from keyword presence; distinguish demonstrated work from claimed familiarity.
- Do not ignore language/work-authorization/logistics notes when they materially affect interview priority; surface them as clarifications for HR rather than making legal or hiring-policy judgments yourself.
- Do not create Confluence tracking pages for every candidate by default; use shortlist intent as the threshold unless Preston asks otherwise.
- Do not lose the cross-candidate comparison context; Preston asked to use the same process, which includes relative ranking against the current reviewed pool.

## Deliverables
At minimum, leave behind:
- `status.md`
- `notes.md`
- raw pasted CV text under `raw/` when the source was chat text
- extracted resume text under `extracted/`
- `candidate-profile.json` once Preston approves page creation

This keeps the review durable and resumable across sessions.
