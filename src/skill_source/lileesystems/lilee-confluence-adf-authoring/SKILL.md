---
name: lilee-confluence-adf-authoring
description: Use when creating or updating Lilee Systems Confluence pages via MCP/API and you must preserve non-targeted ADF exactly, default URLs to inline smart links, keep TOC-first page scaffolding, and enforce SafeART Confluence house rules with validation before write-back. See references/large-page-adf-writeback.md for the large-page REST fallback workflow and references/release-note-section-patching.md for live release-note section-completion patches that must preserve existing evidence tables.
version: 2.1.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [confluence, adf, lilee, safeart, conventions, guardrails]
    related_skills: [native-mcp, hermes-agent]
---

# Lilee Confluence ADF Authoring

## Overview

This skill is the **house policy** for creating and updating Lilee / SafeART Confluence pages through Hermes and Atlassian MCP tools.

Its purpose is not just to help an agent write Confluence pages. Its purpose is to **constrain agent behavior** so page edits stay surgical, reusable, and auditable.

The default operating mode is **fail closed**:
- if the target region is ambiguous, stop;
- if untouched content cannot be preserved exactly, stop;
- if the page needs Jira datasource / smart-link patterns, use ADF, not HTML;
- if page width cannot be explicitly verified through the current tool path, do not claim it was enforced.

## When to Use

Use this skill when:
- creating a new Lilee / SafeART Confluence page,
- updating an existing Confluence page while preserving untouched content,
- inserting URLs, Jira smart links, Jira list blocks, TOC, headings, or page scaffolding,
- preparing reusable ADF templates or page-update workflows for other agents,
- writing to the Lilee Confluence playground or derivative production pages.

Do not use this skill when:
- the task is Jira issue authoring rather than Confluence page authoring,
- the user only wants draft prose and no Confluence mutation,
- a different product/team-specific page standard explicitly overrides these rules.

## Non-Negotiable House Rules

1. **Non-targeted content must not change.**
   - Read the page as ADF first.
   - Preserve untouched nodes verbatim.
   - Replace or append only the exact target node range.
   - Do not normalize whitespace, empty paragraphs, headings, smart-link forms, macro metadata, or local IDs outside the edit region.

2. **Default URL style is inline smart link.**
   - Use `inlineCard` unless the user explicitly asks for plain link, block card, or embed.
   - Plain text links are exceptions, not defaults.

3. **Every governed page starts with TOC.**
   - The first top-level node must be the TOC extension node.
   - If the live page has a stray empty paragraph before TOC and the requested mutation already governs that page/section, treat removal of that leading empty paragraph as an allowed housekeeping fix so the saved page becomes TOC-first again.
   - Before removing it, verify it is truly empty (no text, media, links, mentions, macros, or meaningful attrs beyond the empty paragraph shell).

4. **Default alignment is left.**
   - Use normal paragraph / heading / table structures with no centering wrappers unless explicitly requested.
   - Preserve embed-specific alignment attrs when using Atlassian's native page embed pattern.

5. **Target width is wide, never narrow.**
   - Important limitation: the currently tested MCP page-body path does not expose page-width settings in ADF.
   - Preserve existing width on updates.
   - For newly created pages, treat `wide` as the target policy, but do not claim enforcement unless a separate width/property-capable tool path was used.
   - When the user explicitly asks for full-width tables in the edited region, set those ADF table nodes to a wide layout and verify on read-back that the table attrs persisted.

6. **Status-like fields must use Atlassian status controls.**
   - In any newly authored or explicitly edited region, values such as `Done`, `In Progress`, `Blocked`, `Open`, `Closed`, `Ready`, `Not Started`, `Pass`, `Fail`, or equivalent workflow state labels must be represented with ADF `status` nodes, not plain text.
   - This rule especially applies to table cells, summary grids, rollout trackers, release-readiness sections, and any structured field whose primary purpose is to convey state.
   - Preserve existing status controls outside the edit region exactly as-is.
   - If a status-like value is plain text inside the requested edit scope, normalize it to a status control unless the user explicitly asks to keep plain text.

7. **Assignees in delivery-map tables and due dates in compact work-item lines must use native ADF nodes.**
   - In delivery-map or similar structured work-item tables, assignee cells must be Confluence `mention` nodes, not plain text.
   - When a work item is rendered in compact inline form (for example `[WSx.x] [PD/FE/BE] <ticket-or-short-description> <assignee> <due-date>`), assignee names must be Confluence `mention` nodes, not plain text.
   - Due dates in that compact form must be Confluence `date` nodes, not plain-text dates.
   - If a ticket exists, prefer an inline Jira smart link / `inlineCard`; if no ticket exists, use a short plain-text description in its place.
   - Do not leave a second-line sub-item description under the compact work-item label unless the user explicitly asks for it.

## Forbidden Actions

Never do any of the following unless the user explicitly overrides the rule:

1. Rebuild the whole page for a small localized edit.
2. Use HTML as the default mutation format when ADF is available.
3. Convert existing plain links / inline cards / cards / embeds outside the requested region.
4. Move or remove the TOC from the top of a governed page.
5. Center blocks by default.
6. Claim page width is compliant when the tool path did not verify or set it.
7. Treat an ambiguous heading match as "close enough".
8. Edit a page without a read-back verification step.
9. Leave status-like fields as plain text inside a newly authored or explicitly edited governed region unless the user explicitly asked for plain text.

## Required Workflow

### A. For updates to an existing page

1. Read the target page with `getConfluencePage(..., contentFormat="adf")`.
   - If the user gives a Confluence tiny link (`/wiki/x/<token>`) and direct page read rejects the token or cannot resolve it, first try resolving the token to a numeric page ID with the deterministic tiny-link decode workflow in `references/confluence-tiny-link-resolution.md`, then read the numeric page ID in ADF.
   - If deterministic decode fails or the decoded page is inaccessible/wrong, resolve the numeric page ID via Rovo/CQL search using the expected page title or nearby source terms, then read the numeric page ID in ADF.
   - Record the resolved page ID in the work log/final report.
2. Identify the exact governed region:
   - preferably a uniquely named heading section,
   - otherwise an explicitly agreed node range.
3. Build replacement nodes from `templates/`.
4. If working through a heading-scoped update, use `scripts/confluence_adf_guard.py patch-section` to generate the candidate body.
5. Run `scripts/confluence_adf_guard.py validate` on the candidate body.
6. Before write-back, prove the update is surgical with `scripts/confluence_adf_guard.py verify-section` or an equivalent exact prefix/suffix comparison.
7. Update with `updateConfluencePage(..., contentFormat="adf")` when the tool path can comfortably carry the body payload.
   - If the write-back path rejects the ADF payload at parse time, do **one** diagnostic retry only after confirming the candidate body is still valid JSON and the section patch is still surgical.
   - If the retry still fails, stop repeating the same write call.
   - When the mutation is still valid but the MCP/tool argument path is impractical because the full-page ADF body is too large or awkward to pass as one string, switch to the direct Confluence REST write path instead of giving up:
     - endpoint shape: `https://api.atlassian.com/ex/confluence/<cloudId>/wiki/api/v2/pages/<pageId>`
     - method: `PUT`
     - auth: existing Atlassian Basic token / API token configuration
     - payload discipline: still send the full preserved page body in `atlas_doc_format`, increment `version.number`, and keep the same surgical-preservation guarantees.
   - If neither MCP nor REST can complete the write, save the validated candidate body, replacement-section file, and reviewable draft under the task plan directory, then report the mutation as blocked rather than pretending the page was updated.
8. Read the page back and verify:
   - target change exists,
   - untouched regions remain unchanged,
   - TOC is still the first top-level node,
   - report width as preserved / unverified unless separately enforced.
   - For narrowly scoped Delivery Map table-cell edits, compare the edited cell path explicitly and mask only that cell when checking surgical preservation. Confluence may add or refresh `__confluenceMetadata` on existing links during save; treat that as renderer metadata drift, not authored-content drift, if the text/URLs/nodes outside the target cell are otherwise unchanged.
   - when preserving an existing release-note / review layout, confirm critical table attrs persisted in ADF (for example `layout: align-start`, width, and number-column behavior), not just the rendered appearance.
   - when the user asked for a full carry-forward list (for example all documents in a documentation table), confirm the saved ADF still contains the complete row set after write-back.
   - confirm status-like fields in the edited region persisted as ADF `status` nodes rather than plain text unless the user explicitly approved a plain-text exception.
   - when the edited region contains delivery-map assignee cells, confirm those cells persisted as ADF `mention` nodes rather than plain text.

### D. When editing an existing release note / release review page to match prior releases

1. Read the target page in ADF.
2. Read the adjacent precedent release pages in ADF as structural references before editing.
3. Compare the governed section node-for-node, especially headings, table attrs, row counts, smart-link forms, and numbering structure.
4. Treat missing carried-forward rows as a structural defect, not a copy-edit issue.
5. If the legacy table is left-aligned, preserve that explicitly in ADF with the corresponding table attrs instead of trusting renderer defaults.
6. After write-back, re-read the target page in ADF and verify both content completeness and structural attrs.
7. If patching multiple sections in one pass, verify each later section against the already-staged intermediate document rather than the original untouched base; otherwise a legitimate earlier edit can make `suffix_same` look falsely broken for the later section.

### E. When updating a KPI / roadmap page from a delivery map while following a prior-half KPI page

1. Read three sources in ADF before editing:
   - the live target KPI page,
   - the prior-half KPI page used as the format reference,
   - the source delivery-map page.
2. Treat the prior-half KPI page as the **packaging precedent** and the delivery map as the **scope / schedule source of truth**.
3. Preserve the target page's surrounding layoutSection structure when only one feature section is being refreshed.
4. Repackage delivery-map workstreams into KPI form rather than pasting tables verbatim:
   - keep the scenario-style blockquote,
   - keep source links as inline smart links,
   - carry workstream release labels as Atlassian status nodes,
   - summarize each workstream in manager-readable prose, then nest ticket / assignee / due / deliverable details underneath.
5. For right-column `Summarized milestones` style content, group by release wave and keep release labels as status controls rather than plain text.
   - If the page already uses one shared summary column for multiple feature sections, preserve the existing summaries and append a feature-specific label + milestone list for the newly edited section instead of folding new milestones into the previous feature's list.
   - When the source delivery map has been re-baselined and release waves collapsed or shifted, rebuild the KPI summary to the **current unique release set from the source workstreams** rather than preserving stale extra waves. It is acceptable for the milestone count to shrink (for example 6 waves -> 5 waves) when the source now rolls up later work into earlier releases.
6. Mirror the source delivery map's release labeling faithfully, but normalize obvious typography drift such as `SafeARt` vs `SafeART` so the KPI page uses one consistent product casing.
7. If the target KPI page drifted from house rules (for example an empty paragraph before TOC), fix that only when you can prove the change is housekeeping-only and does not modify user-authored content.
8. Read the saved page back and verify both the packaging layer (section structure, summary column, status nodes) and the source-carryover layer (representative workstream titles / dates / tickets) persisted.
   - For compact KPI work-item lines that use native Confluence `date` nodes, verify persisted due dates by **reading the date nodes back to ISO dates**, not by grepping for raw millisecond timestamps in serialized ADF. Timestamp values can differ by timezone/rendering assumptions and make a good write look false-negative.

### B. For creating a new governed page

1. Start from `templates/page-skeleton-with-toc.json`.
2. Keep the TOC node as the first top-level node.
3. Default links to inline smart links.
4. Avoid centered layouts unless explicitly requested.
5. Use Atlassian status controls for status-like fields in authored tables or structured summaries.
6. Validate the draft ADF with `scripts/confluence_adf_guard.py validate --require-toc-first --forbid-plain-links` when the page should follow the strict default policy.
7. After creation, read the page back in ADF and verify the expected node types survived Confluence round-trip, including `status` nodes for status-like fields.

## Enforcement Script

Use the bundled script when possible:

- `scripts/confluence_adf_guard.py`

### What it does

1. `validate`
   - checks root type is `doc`
   - checks TOC is first when required
   - flags plain links when strict inline-link policy is enabled
   - flags centered layout nodes except the known native embed exception

2. `patch-section`
   - replaces only the **body** of a uniquely named heading section
   - preserves the heading node itself
   - preserves everything outside the section untouched

3. `verify-section`
   - proves only the chosen section body changed
   - proves prefix/suffix outside that section are identical
   - can also assert TOC remains first

### Typical commands

```bash
python scripts/confluence_adf_guard.py validate page.json --require-toc-first --forbid-plain-links

python scripts/confluence_adf_guard.py patch-section \
  --base before.json \
  --heading "Target Section" \
  --replacement replacement.json \
  --out candidate.json

python scripts/confluence_adf_guard.py verify-section \
  --before before.json \
  --after candidate.json \
  --heading "Target Section" \
  --require-toc-first
```

## Template Files

- `templates/page-skeleton-with-toc.json` — starter governed-page ADF body
- `templates/adf-snippets.json` — reusable URL / Jira node snippets
- `templates/final-report-template.md` — required completion-report shape
- `references/conventions.md` — rationale, caveats, and tested behavior
- `references/agent-hand-off-contract.md` — short contract to paste into downstream-agent tasks
- `references/large-page-adf-writeback.md` — large-page REST fallback, including the live-body drift guard before PUT and post-write verification of representative edited values
- `references/confluence-tiny-link-and-blank-page-fallback.md` — fallback for resolving `/wiki/x/<tiny>` links to numeric page IDs when MCP tiny-link resolution fails, plus the narrow blank-page Markdown fallback exception
- `scripts/confluence_adf_guard.py` — local validator / surgical patch helper

## Required Final Report Fields

When you finish a Confluence mutation under this skill, your final report must include:

- target page title and page ID,
- whether the task was create vs update,
- exact governed section / region changed,
- whether ADF validation passed,
- whether surgical-preservation verification passed,
- whether TOC-first was preserved,
- whether status-like fields in the edited region were represented as Atlassian status controls or an explicit exception was approved,
- whether page width was preserved, explicitly enforced, or still unverified.

## Common Pitfalls

1. **Using HTML instead of ADF for Jira lists.**
   HTML write-back can fail validation for datasource-backed Jira list blocks.

1a. **Giving up when a Confluence tiny link does not resolve directly.**
   If `/wiki/x/<tiny>` or the bare tiny token fails in `getConfluencePage`, do not immediately ask the user for the page ID. First try search by title/context; if still needed, decode the classic tiny token to a numeric page ID and verify by re-encoding. See `references/confluence-tiny-link-and-blank-page-fallback.md`.

1b. **Over-applying ADF-only discipline to a genuinely blank documentation page.**
   ADF remains the default, especially for governed or surgical edits. But if the target page is effectively blank and the content is a concise explanatory reference, a Markdown write can be an acceptable exception after generating/validating the intended structure and reading back representative saved content. Report the exception explicitly and do not claim TOC/status-control compliance that the Markdown path did not preserve.

1c. **Using Markdown write-back on an existing structured page with tables.**
   Markdown write-back can strip Confluence table attrs such as `layout: align-start`, explicit `width`, per-cell `colwidth`, `localId`, and status controls. Do not use Markdown for existing candidate-tracking, release, delivery-map, KPI, or other structured pages unless the user explicitly accepts possible formatting loss. If a Markdown write-back already happened and the user reports table alignment/width drift:
   - read a same-family reference page in ADF when available;
   - copy the reference table pattern, especially `layout: align-start`, table `width`, and every cell's `colwidth` array;
   - avoid substituting `layout: default` or `displayMode: fixed` unless the reference page actually uses them;
   - write back with ADF, preferably direct Confluence REST when the MCP argument/response path is too large;
   - read back in ADF and verify all table attrs and per-cell `colwidth` values match the reference pattern.

1d. **Overwriting candidate-tracking page comments with an evidence dump.**
   Candidate tracking pages use concise comments, not full interview transcripts. For Stage 2 / technical-interview comments, preserve the scoring table and replace only the comments region after it. Write `Comments:`, `Interview Result: <Passed/Rejected>`, then about 5–7 bullet items: preparation/presentation, positive technical evidence, major technical gaps, testing/quality signal, and final recommendation. Keep the detailed raw notes in the task plan directory, not in the Confluence page. After write-back, verify the Stage 3+ suffix is unchanged and table attrs still match the reference page.

1e. **Over-editing a Delivery Map when only a missing Ticket cell must be filled.**
   For requests like "open the WSx.y ticket and paste it back into the ticket cell," read the Delivery Map in ADF, create the Jira ticket from the row's scope, then replace only that row's Ticket cell paragraph content with a Jira `inlineCard`. Preserve the cell, row, table, and page attrs/localIds. If the full-page ADF is too large for the normal MCP update path, use the direct Confluence REST `atlas_doc_format` fallback with a live-body drift guard and read-back verification. Validate the target cell URL, TOC-first, and table attrs after save.

2. **Rewriting the entire page for a small change.**
   This violates the non-targeted-content rule.

3. **Heading ambiguity.**
   If a heading appears multiple times, do not guess. Add disambiguation or stop.

4. **Claiming wide-layout compliance from body ADF alone.**
   The tested MCP page-body path does not expose width in body reads/writes.

5. **Allowing plain links to spread by accident.**
   Inline smart links are the default policy; plain links must be intentional exceptions.

6. **Skipping read-back verification.**
   Confluence can rewrite structure on round-trip; verify what actually persisted.

7. **Matching the prose style but not the section skeleton of a prior release note.**
   For derivative artifacts such as SafeART release notes, "follow the previous release note" means more than tone. Before drafting, inspect the prior page's actual section structure and mirror the section mechanics the user is implicitly reviewing against — for example:
   - 2.1 often expects `The Release Build` plus `Documentation` with a documentation table,
   - 2.3 may expect a `Planned | Actual` comparison table rather than narrative bullets,
   - 2.5 may expect the full QA hierarchy (`Uphill Testing`, `Regression Testing`, and their nested subsections) rather than a flatter summary.
   If you only copy the writing voice and not the layout pattern, expect a review correction.

8. **Rewriting QA test-case wording when a prior release note already has an acceptable row.**
   For SafeART release-note QA sections, if the same scenario already exists in the previous release note, copy that row wording directly unless the user explicitly asks to rewrite it. Treat new work as two buckets:
   - overlap with prior release note → reuse prior wording,
   - present only in the source test-case page → simplify into the prior release note's row style.
   Also preserve any explicit user-provided classification rules (for example, exactly which suites count as uphill vs manual vs automated) instead of inferring your own split from the source page taxonomy.

9. **Flattening nested lists during Markdown-to-ADF conversion.**
   When generating ADF from Markdown drafts, preserve nested bullet structure as nested `bulletList` / `orderedList` nodes inside the parent `listItem`. Do not flatten child bullets with textual prefixes like `→`; Confluence read-back will show noisy top-level bullets and the page will look less professional. After write-back, read back representative nested-list sections (for example phase models) and verify the structure rendered as nested lists.

10. **Using plain text for status columns in governed tables.**
   For any status-like column or summary field in scope, use Atlassian status controls in ADF instead of plain text labels unless the user explicitly approved an exception.

## Release-note inheritance rule

When updating a release note that is explicitly described as "follow the 0.xx release note" or "match the previous format":

1. Read the previous release note first, not just the target page.
2. Extract the exact section skeleton for the sections in scope.
3. Preserve that skeleton unless the user explicitly asks to redesign it.
4. Only then adapt the content and tone for the new release scope.
5. If you intentionally deviate, call out the deviation before writing so the user can approve it.

## Verification Checklist

- [ ] Read target page in ADF before editing
- [ ] Exact governed section or node range identified
- [ ] Untouched nodes preserved exactly
- [ ] URLs default to inline smart links unless explicitly overridden
- [ ] Status-like fields in the edited region use Atlassian status controls unless explicitly overridden
- [ ] TOC exists at top of new / governed pages
- [ ] Update path used ADF, not ad-hoc HTML
- [ ] Validation completed before write-back
- [ ] Read-back verification completed after write-back
- [ ] Final report states width as preserved / enforced / unverified honestly
