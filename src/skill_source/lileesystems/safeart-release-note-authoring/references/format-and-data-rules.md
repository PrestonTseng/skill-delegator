# SafeART Release Note Format and Data Rules

## Discovery rule
- Do not hardcode SafeART 0.20 as the permanent golden copy.
- First discover the latest published SafeART release note in Confluence.
- Read that page in ADF and use it as the live formatting baseline.

## Known historical anchors
- SafeART 0.20 Release Note: page `3806560282`
- Previous known release note for wording reuse: page `3736535112`
- Uphill Test Cases: page `3524067749`
- Atlassian cloudId: `302f7dfa-a172-4986-b4ae-efd7021f110a`

## Structural rules
- Read the target page and the latest release-note baseline in ADF first.
- TOC must remain the first top-level node.
- Preserve existing numbering / heading hierarchy.
- Patch only requested sections.

## Formatting rules observed from recent SafeART release-note ADF snapshots
- Tables are commonly left-aligned (`layout: align-start`).
- Tables are commonly full width (`width: 1800` / `1800.0`).
- Recent table families:
  - documentation = 4 columns
  - known issues = 5 columns
  - QA tables = 7 columns
  - revision = 3 columns
- Link-style text has used Atlassian blue `#0747a6` in recent pages.
- If exact widths matter, copy the exact `colwidth` arrays from the live baseline ADF page instead of approximating them.

## 2.1 rules
- Ask the user for release version number.
- Ask the user for release timing / date wording.
- Never guess those values.

## 2.2 rules
- Content is flexible and release-specific.
- Existing tables / screenshots under live subsections must be preserved exactly.
- Bound claims so the section does not overstate undelivered scope.

## 2.4 rules
- Follow the latest baseline section structure.
- In the currently known modern pattern, columns are:
  1. Priority
  2. Scope
  3. Duration
  4. Summary
  5. Resolution / Impact & Mitigation
- Query release bugs with JQL.
- Verify sprint-only filtering does not miss intended release bugs.
- Freeze the final intended cohort before publication.
- Do not invent mitigations; keep `--` when none is supported.

## 2.5 rules
- Ask the user which uphill cases are new / updated.
- Ask the user which manual tests were executed.
- Read the previous release note first.
- Reuse prior wording when the same scenario already exists.
- Read the Uphill Test Cases page and detect new automated rows.
- Preserve any user-provided inclusion / exclusion rule for automation scope.
- Current known QA columns:
  1. Test Suite
  2. Suite Name
  3. Case #
  4. Summary
  5. Given
  6. Expected Result
  7. Result

## Write-back rules
- Use `lilee-confluence-adf-authoring`.
- Validate the candidate ADF before write-back.
- Re-read after publish and verify the saved structure.
