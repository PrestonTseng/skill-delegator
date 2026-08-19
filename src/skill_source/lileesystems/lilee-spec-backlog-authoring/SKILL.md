---
name: lilee-spec-backlog-authoring
description: Author LILEE spec/backlog Confluence pages in the Seshat 2.0 concise format, expanding toward TSR-style detail only when complexity requires diagrams, state models, or domain explanation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [lilee, confluence, backlog, spec, tapas, safeart]
    related_skills: [lilee-confluence-adf-authoring, tapas-knowledge, jira-ticket-writer]
---

# LILEE Spec / Backlog Authoring

## Purpose

Use this skill to create or refactor LILEE / TAPAS / SafeART **spec + backlog** Confluence documents into one consistent structure.

The house default is the **Seshat 2.0 pattern**: concise, precise, concrete, and acceptance-criteria driven. Use the **TSR pattern** only when the topic itself needs extra explanation, sequence diagrams, state models, or operational responsibility boundaries.

This skill defines the document structure, section intent, table widths, and acceptance-criteria style. When actually creating or updating Confluence, also load `lilee-confluence-adf-authoring` and write in ADF with read-back verification.

## Source Precedents

Read the live source pages before claiming they are the current standard:

- **Primary precedent:** `Backlog - Seshat 2.0` — page ID `3713728564`, tiny link `https://lileesystems.atlassian.net/wiki/x/NABb3Q`
- **Complex precedent:** `Backlog - Temporary Speed Restriction (TSR)` — page ID `3714482215`, tiny link `https://lileesystems.atlassian.net/wiki/x/J4Bm3Q`

Observed precedent rules:

1. Seshat 2.0 is the preferred baseline: TOC first, short Why, clear User & Trigger, terminology only when useful, concise system design, scenario-driven story breakdown, specific acceptance criteria, Definition of Done, Revision.
2. TSR is the expansion model for complex operational topics: add state/status model, responsibility split, data flow, diagrams, detailed paths, key decisions, and stakeholders only because the domain requires them.
3. Do not make every backlog page as long as TSR. Complexity must justify extra sections.
4. For shared principle / policy / convention pages, read `references/principle-spec-pages.md`; these pages should usually be shorter than Seshat-style feature specs and should push implementation details into downstream design docs.

## When to Use

Use when the user asks to:

- create a spec / backlog page;
- normalize a backlog document format;
- turn planning notes into a Confluence-ready backlog spec;
- split an epic/spec into scenario-level stories with acceptance criteria;
- prepare a source page before Jira tickets are created.

Do not use as the primary skill when the output is only Jira tickets; use `jira-ticket-writer` after the backlog source page is stable.

## Required Source-of-Truth Workflow

1. Read the user's named Confluence/Jira sources through Atlassian MCP.
2. If there are existing related backlog pages, read them before drafting.
3. Separate confirmed source facts from assumptions.
4. Do not invent subsystem behavior. Mark unknowns as open questions.
5. If the topic touches operating rules, train movement authority, signaling, blue-signal protection, door/PSD responsibility, radio/communications, or regulatory boundaries, load the relevant railroad/railway source skill and cite exact rule/section text.

## Default Document Skeleton

Use this section order unless the user explicitly asks otherwise:

1. TOC macro — first node on the page.
2. H1 page title — omit if the Confluence page title already serves as H1 and the precedent page does not need a visible H1.
3. `Why`
4. `User & Trigger`
5. `Terminology`
6. `System Design`
7. `In Scope / Out of Scope`
8. `Diagrams` — conditional; include only when prose is not enough.
9. `Scenarios`
10. `Story Breakdown`
11. `Design Considerations`
12. `Key Decisions` — conditional for decision-heavy topics.
13. `Impacted Domains / Dependency Assumptions`
14. `Definition of Done`
15. `Open Questions / Risks`
16. `Required Follow-up Actions`
17. `Revision`

For concise pages, sections 12–16 may be short, but they should be explicit if they affect planning or delivery.

## Section Rules

### Why

- Explain the operational/product reason, not the implementation wish list.
- Target 3–5 short paragraphs.
- State what current gap exists, why it matters, and what the feature changes.
- Include a boundary sentence when important, e.g. “This is not a TAPAS runtime dependency.”

### User & Trigger

- Use bullets.
- Name user roles and the event that causes them to need the feature.
- Keep role labels bold and concrete.

Example shape:

```markdown
* **Developer** — needs to debug a failed TAPAS scenario by inspecting MQTT traffic across services.
* **QA** — needs evidence from a test run and wants to compare recorded behavior after the run.
```

### Terminology

- Include only terms needed to avoid ambiguity.
- Prefer short definition lists for concise pages.
- Use a table only when terms are numerous or definitions need side-by-side scanning.

### System Design

Include only the design detail needed to make the stories and acceptance criteria unambiguous.

Good subsections:

- responsibility split;
- architecture boundary;
- state/status model;
- data flow;
- phase model;
- dependency behavior.

Do not drift into implementation task decomposition unless Preston explicitly asks.

### In Scope / Out of Scope

- Make boundaries explicit.
- Out of scope is as important as in scope.
- Use bullets grouped by feature phase or domain when helpful.

### Diagrams

Add diagrams only when they reduce ambiguity. Use TSR-style sequence diagrams for multi-actor flows, state transitions, or runtime authority paths.

Diagram rules:

- Name every participant with its owning domain, e.g. `JPS`, `Bulletin Manager (SS)`, `MA Manager (SS)`, `ADS`.
- Split user operation path from runtime effect path when both exist.
- Use `alt`, `else`, and `loop` blocks for branching behavior.
- Keep diagram text source-faithful; do not improve wording unless the user approved the wording change.
- If using Mermaid, verify syntax before publishing when possible.

### Scenarios

Each scenario should have:

- heading: `Scenario N — Name` or `Path N — Name`;
- short summary or user situation;
- preconditions when needed;
- expected result or workflow.

Use scenarios to explain behavior; do not hide acceptance criteria inside only prose scenarios.

### Story Breakdown

Use story headings rather than one giant table by default.

Required shape:

```markdown
### Story N — Short capability name

**Scenario:** One sentence describing the user's observable outcome.

**Spec / Acceptance Criteria:**

* Concrete criterion 1.
* Concrete criterion 2.
* Concrete criterion 3.
```

Acceptance criteria must be:

- observable or testable;
- specific about actor, state, data path, or UI behavior;
- scoped to one story;
- free of vague verbs such as “support properly” unless followed by exact behavior;
- explicit about failure, empty, timeout, invalid, offline, or fallback behavior when relevant.

### Design Considerations

Use for known tradeoffs and implementation-readiness constraints. Keep each item as `Bold topic — explanation`.

### Key Decisions

Use only when decisions are likely to be challenged later or need to constrain future tickets. Include rationale.

### Impacted Domains / Dependency Assumptions

Always make cross-domain dependencies explicit. For TAPAS, common domains include SS, JPS, MMS, WSS, ADS, TriOps, QA, Design, DevOps/testbed, and ACES.

### Definition of Done

Epic-level DoD should summarize the observable outcomes, not restate every story's criteria. It must include cross-domain boundary and dependency expectations.

### Open Questions / Risks

Use this section when a requirement cannot be finalized from the source material. Do not bury assumptions in acceptance criteria.

### Required Follow-up Actions

List source follow-ups, review needs, Jira-creation next steps, diagram verification, or stakeholder confirmation.

### Revision

Every governed page ends with a Revision table using the canonical width spec below.

## Table Width Standard

Use explicit table and column widths every time. Default page/table width is **1642 px**, matching the observed Seshat revision-table precedent.

When writing ADF, set table attrs equivalent to:

```json
{
  "layout": "align-start",
  "width": 1642
}
```

Set each table cell/header `colwidth` to the exact column width. When using HTML conversion, preserve equivalent `data-width` and `data-colwidth` attributes.

Canonical table specs:

### Terminology table

- Table width: `1642`
- Columns:
  - `Term` — `300`
  - `Definition` — `1342`

### Status / State model table

- Table width: `1642`
- Columns:
  - `Status` / `State` — `330`
  - `Description` — `1312`

### Impacted Domains / Dependency Assumptions table

- Table width: `1642`
- Columns:
  - `Domain` — `260`
  - `Impact` — `552`
  - `Dependency Assumption` — `570`
  - `Owner / Source` — `260`

### Key Decisions table

- Table width: `1642`
- Columns:
  - `#` — `90`
  - `Decision` — `600`
  - `Rationale` — `952`

### Open Questions / Risks table

- Table width: `1642`
- Columns:
  - `ID` — `90`
  - `Topic` — `300`
  - `Question / Risk` — `722`
  - `Impact` — `310`
  - `Owner / Next Step` — `220`

### Follow-up Actions table

- Table width: `1642`
- Columns:
  - `ID` — `90`
  - `Action` — `752`
  - `Owner` — `260`
  - `Due / Trigger` — `240`
  - `Status` — `300`

### Revision table

Use the Seshat observed revision-table precedent:

- Table width: `1642`
- Columns:
  - `Date` — `163`
  - `Description` — `1214`
  - `Author` — `262`

## Status Controls

For Confluence pages, status-like values must use Atlassian status nodes, not plain text, in any newly authored or edited table:

- Not Started
- Open
- In Progress
- Blocked
- Ready
- Done
- Pass / Fail
- Scheduled / Effective / Expired
- Not Enforced / Enforced

## Concision Rules

Prefer Seshat-style precision:

- One idea per paragraph.
- Bullets over dense paragraphs for requirements.
- Do not repeat the same requirement in Why, Scenario, Story, and DoD unless each section adds a different level of detail.
- Put complex behavior in scenarios or diagrams, not in vague AC bullets.
- Add sections only when they prevent ambiguity.

### Principle / policy page exception

When the user clarifies that a page is a **principle**, **policy**, or **common convention** page rather than a runtime behavior spec, do not force the full backlog skeleton. Keep the page concise and authoritative. A good minimal structure is:

1. `Why`
2. `Key Terms` — only terms needed by a reader without project background
3. `Scope` — explicit in/out boundaries
4. `Principles` / `Convention`
5. `Priority` or `Ownership` — only if the user provided it
6. `Required Development Flow` — grouped lifecycle, not task decomposition
7. `Design Document Requirements` — what downstream component docs must define
8. `Acceptance Criteria`
9. `Open Questions`
10. `References`
11. `Revision`

Pitfalls:

- Do not add Scenarios, Impacted Domains, Definition of Done, Design Considerations, or Key Decisions just because they are in the default skeleton; add them only when the principle page needs them.
- If the user asks to “follow Seshat format” for a principle/convention page, add concise `User & Trigger`, `Scenarios`, and `Story Breakdown` even if implementation details remain delegated. Keep scenarios explanatory and source-faithful, using representative examples from the strongest service-level design source. Keep story breakdown as planning gates, not engineer tasks.
- For principle pages that coordinate per-service or per-component work, story breakdown should reflect the requested priority order and lifecycle gates. A proven pattern is three stories per service/component: (1) study/review → service ARK Code design document, (2) study/review → implementation architecture design, (3) implement according to finalized architecture.
- If details are explicitly delegated to per-component/per-service design docs, keep the page at the shared-principle level and list those details as downstream document requirements.
- When the story breakdown already represents the lifecycle gates, do not keep separate standalone sections such as `Required Development Flow` or `Service Design Document Requirements` if Preston asks for Seshat-style story packaging. Fold those requirements directly into the relevant story acceptance criteria: design-document stories carry required document contents; architecture-design stories carry study/review and approval gates; implementation stories carry the dependency on finalized architecture.
- Acceptance criteria should verify the convention and downstream-document gates, not just restate that the page contains text.
- When using an external/source system as a model (for example "follow ADS where applicable"), split mandatory shared constraints from source-specific examples.

## Complexity Escalation Rules

Escalate from Seshat-style concise page to TSR-style detailed page only when at least one is true:

1. Multiple runtime authorities or systems share responsibility.
2. Status/state transitions affect behavior.
3. Vehicle movement, MA, signaling, authorization, door/PSD responsibility, or operating-rule boundaries are involved.
4. The feature has multiple abnormal paths that must be accepted or rejected explicitly.
5. Sequence diagrams are needed to prove who sends what to whom.
6. Cross-team responsibility must be locked before Jira tickets can be safe.

## Confluence Authoring Requirements

When creating/updating a Confluence page:

1. Load `lilee-confluence-adf-authoring`.
2. Read source and target pages in ADF.
3. Preserve TOC as the first top-level node.
4. Use inline smart links for Jira/Confluence URLs unless the user asks otherwise.
5. Preserve untouched nodes exactly for updates.
6. Enforce table widths in the edited/new region.
7. Use status nodes for status-like table values.
8. Read back and verify structure, widths, and status nodes.

## Output Checklist

Before finalizing a spec/backlog artifact, verify:

- [ ] Why is explicit.
- [ ] In scope and out of scope are explicit.
- [ ] Impacted domains are explicit.
- [ ] Dependency assumptions are explicit.
- [ ] Acceptance criteria are concrete and testable.
- [ ] Open questions / risks are captured instead of guessed.
- [ ] Required follow-up actions are listed.
- [ ] Tables use explicit table width and column widths.
- [ ] Diagrams are included only when needed and are source-faithful.
- [ ] No subsystem behavior was invented beyond source material.
