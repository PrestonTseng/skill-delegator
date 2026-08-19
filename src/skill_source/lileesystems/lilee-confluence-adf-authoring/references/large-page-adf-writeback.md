# Large-page ADF writeback fallback for Lilee Confluence pages

Use this when a section-level Confluence edit must preserve the user's latest live edits, but the normal MCP page-update path is impractical because the full ADF body must be supplied as one very large string.

## When to use
- You already read the live page as ADF and identified one target section to replace.
- You need surgical preservation of all non-target nodes.
- The replacement content is easier to build locally and then write back as a full ADF page body.
- The user has manually tweaked the live page and you must patch against the latest live version, not an older local draft.

## Recommended flow
1. Fetch the **current live page body** from Confluence REST as `atlas_doc_format` and save it locally.
2. Build the replacement section locally.
3. Run `confluence_adf_guard.py patch-section` against the live ADF snapshot.
4. Run `confluence_adf_guard.py verify-section` and confirm:
   - `prefix_same: true`
   - `suffix_same: true`
   - `surgical_ok: true`
   - `toc_first: true`
5. Minify the final ADF JSON before writeback if needed.
6. Re-fetch the live page immediately before PUT and compare its full ADF body with the snapshot you patched against.
   - Compare parsed `atlas_doc_format` JSON semantically, not raw string length or byte-for-byte serialization, because MCP output and REST output may differ only by insignificant JSON formatting.
   - Canonicalize renderer output before deciding that write-back drift occurred: ignore generated `localId`, `__confluenceMetadata`, generated macro IDs, TOC macro `_parentId`, and renderer-added media metadata such as `__fileName`, `__fileMimeType`, and `__fileSize`; treat integral floats and integers as equivalent; for tables, also ignore renderer-added `colspan: 1` / `rowspan: 1` defaults and treat integer/float `colwidth` values as equivalent; remove empty `attrs` / empty text nodes; merge adjacent text nodes with identical marks; compare a text node's `marks` as an order-insensitive set after canonicalizing each mark (Confluence may swap semantically independent marks such as `link` and `textColor` during persistence); and treat `/pages/{id}/{title-slug}` and `/pages/{id}` as the same Confluence smart-link target. Confluence commonly applies all of these normalizations during persistence. Do not ignore actual text, mark content, node-type, media-ID/collection, target page ID, or table-structure changes.
   - If differences remain after canonicalization, inspect the exact JSON paths and treat them as real drift until proven otherwise.
   - If the body drifted semantically, abort and rebuild from the refreshed live body instead of overwriting possible user edits.
   - For structure-rewrite transforms (for example compacting work-item rows across many planning tables), do not reuse the stale candidate body after drift. Re-run the transformation from the freshly fetched live ADF, then re-validate before PUT.
   - This drift guard matters on large planning / release pages that the user may still be editing while you prepare the patch.
7. Read the live page metadata again to get the latest version number.
8. PUT the full page body through Atlassian Confluence REST API with:
   - incremented version number
   - explicit version message
   - unchanged title
   - `body.representation = "atlas_doc_format"`
   - `body.value = <minified ADF JSON string>`
9. Re-fetch the page after writeback and verify:
   - version incremented
   - target heading still exists
   - newly added issue keys / markers are present in the persisted body
   - representative formula / computed values or other edited cells persisted exactly as expected when the page contains calculated planning fields

## Why this matters
This fallback preserves the Lilee rule: read live ADF first, patch only the intended section, and verify persisted structure after writeback.

## Release-note-specific reminder
When the user has already tuned wording in a live release-note table, re-read the live page first and preserve the user's wording style unless the source material requires a correction.

## Pitfall
Do **not** patch from an older local ADF draft when the user says they already adjusted the live table. Always refresh from the live page first, then patch.
