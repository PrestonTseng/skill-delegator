# Agent hand-off contract for governed Confluence pages

Use this when instructing another agent to modify a Lilee Confluence page.

## Required preamble

Load skill `lilee-confluence-adf-authoring` before doing anything else.

## Hard constraints

1. Read the page as ADF first.
2. Preserve all non-targeted nodes exactly.
3. Use ADF, not HTML, for write-back.
4. Default URLs to inline smart links.
5. Keep TOC as the first top-level node.
6. Do not claim page width was enforced unless your tool path explicitly supports width/property mutation.
7. If the target section is ambiguous, stop and report ambiguity instead of guessing.
8. Read the page back after update and verify the persisted structure.

## Required deliverables

- the updated page,
- the exact section changed,
- a validation result,
- a surgical-preservation result,
- an honest width-status statement.
