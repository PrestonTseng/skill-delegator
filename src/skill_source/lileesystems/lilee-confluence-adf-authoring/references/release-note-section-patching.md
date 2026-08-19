# Release-note section completion on live Confluence pages

Use this pattern when Preston says a live release-note section already exists and wants you to "complete the chapter" without disturbing user-edited tables or neighboring content.

## When this applies
- The target Confluence page already contains the heading structure.
- One or more sections contain user-authored tables or screenshots that must remain unchanged.
- The task is to add framing prose, clean up incomplete wording, or finish subsection conclusions.

## Working rule
Patch only the body of the named section heading. Do not rebuild the surrounding chapter from an older local draft.

## Recommended sequence
1. Read the live page in ADF first.
2. Identify the exact heading(s) to modify.
3. Reuse the live table / media nodes exactly as they appear in the current ADF.
4. Build replacement nodes that add only the missing prose before / after those preserved nodes.
5. If updating multiple adjacent sections, patch them incrementally on a staged document.
6. Verify each patch surgically:
   - `prefix_same: true`
   - `suffix_same: true`
   - `surgical_ok: true`
   - `toc_first: true`
7. Write back the full ADF body through the Confluence REST fallback when the MCP page-update path is impractical for large payloads.
8. Re-read the saved page and confirm the exact new prose markers are present.

## Important pitfall
When verifying a later section after an earlier staged patch, compare the later patch against the staged intermediate document, not against the original untouched base. Otherwise `suffix_same` can look false even though the final patch is correct, because the earlier section change legitimately shifts the later section's suffix.

## Release-note-specific reminder
For GUI-improvement or automation-coverage sections, preserve the user's evidence tables exactly and limit edits to narrative framing, incomplete sentences, and conclusion text unless the user explicitly asks to rewrite the table content.
