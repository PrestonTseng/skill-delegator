# Large-page smart-link writeback and verification

Use this when updating an existing Lilee Confluence page in ADF and the change is narrowly targeted (for example: filling ticket cells, replacing placeholder text with Jira smart links, or updating one section in a large delivery-map page).

## Durable pattern

1. **Read the page as ADF first** and identify the exact target nodes by stable structure or `localId`.
2. **Patch only the intended nodes**. For ticket backfill, replace the target paragraph/table-cell paragraph content with an `inlineCard` pointing to the Jira URL.
3. **Preserve the rest of the ADF exactly**. Do not rebuild surrounding sections, tables, or macro structure if you can patch the existing nodes in place.
4. **Keep TOC first** if the page already starts with a TOC macro.
5. **Validate locally before write-back**:
   - confirm every intended target `localId` was patched
   - confirm no unexpected sections changed
   - confirm the first node is still the TOC when the page previously had one
6. **Refetch the live page immediately before PUT** and patch that freshly fetched body, not an older cached ADF blob. This avoids stale-body drift when the stored body differs from the current live representation.
7. **Write back with a version bump and explicit version message**.
8. **Read back to verify persistence** using at least two views:
   - ADF read-back: confirm the expected `inlineCard` URLs are present in the target nodes
   - markdown or REST read-back: confirm the final page body contains the expected Jira keys/URLs

## Pitfalls

- **Do not trust an older saved REST payload as the final PUT base** for a large page. Even when the version number has not advanced, the live ADF body can differ from an earlier fetched blob. Refetch first, then patch the fresh body.
- **Do not rewrite placeholder-adjacent sections wholesale** when only one ticket field needs updating. Preserve non-targeted nodes exactly.
- **Guard against silent misses**: if any expected target `localId` is not found, stop and investigate instead of guessing a replacement location.
- **Validator warnings are not always caused by your patch**. Distinguish pre-existing page structure issues from newly introduced changes before deciding whether to block the write.

## Good fit examples

- Delivery Map pages where a Story Ticket field and work-item Ticket column need Jira links inserted
- Large pages where whole-body PUT is required but the actual mutation surface is small
- Pages with TOC-first structure that must be preserved exactly
