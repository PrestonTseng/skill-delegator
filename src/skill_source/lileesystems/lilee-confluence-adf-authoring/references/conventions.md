# Confluence ADF conventions for Lilee / SafeART pages

## Scope

These conventions are derived from live experiments against the playground page `Confluence Style Check` (`/x/BYCp4g`) and its child page `ADF Child Page Baseline 2026-06-18 06:00 UTC`.

## Hard rules

1. **Non-targeted content must remain byte-for-byte / node-for-node unchanged whenever possible.**
   - Read the page as ADF first.
   - Preserve all untouched nodes verbatim.
   - Only replace or append the exact node range you intend to change.
   - Do not normalize spacing, headings, empty paragraphs, localId fields, or smart-link forms outside the target region.

2. **Default URL style = inline smart link.**
   - Preferred node:
     - `{"type":"paragraph","content":[{"type":"inlineCard","attrs":{"url":"..."}}]}`
   - Use plain links only when a raw URL text string is explicitly wanted.
   - Use block card or embed only when the presentation requirement calls for them.

3. **Page width convention = wide by default; never narrow.**
   - Important limitation: page width is **not represented in the ADF body** returned by current MCP page read/write tools.
   - Current tool surface used here cannot explicitly set or verify page width through the page body alone.
   - Therefore, agents should:
     - preserve existing width on updates,
     - assume new API-created pages may need a follow-up width-setting step outside the current body ADF,
     - never claim width was enforced unless they used a tool that explicitly sets page properties / width.

4. **Default alignment = left.**
   - For standard paragraphs and headings, left alignment is achieved by using default paragraph/heading nodes with no centering wrappers.
   - Do not use layout sections or alignment parameters that center content unless explicitly requested.
   - For images/media/tables, prefer default/left-start layout settings and avoid center-specific attrs.
   - Exception: Atlassian's native page embed macro currently reads back with `alignment: center` in its macro params; preserve that if using the native embed pattern.

5. **Every page starts with TOC.**
   - Use a top-of-body extension node:
     - `{"type":"extension","attrs":{"layout":"default","extensionType":"com.atlassian.confluence.macro.core","extensionKey":"toc"}}`
   - This pattern was successfully written to the child playground page.

## Proven working node patterns

### TOC
- Minimal working ADF node:
```json
{
  "type": "extension",
  "attrs": {
    "layout": "default",
    "extensionType": "com.atlassian.confluence.macro.core",
    "extensionKey": "toc"
  }
}
```

### URL styles
- Plain link = text node + `link` mark
- Inline = `inlineCard`
- Block card = `blockCard`
- Embed = `extension` with `extensionKey: "native-embed:page"`

### Jira work item styles
- Link = text node + `link` mark
- Inline = `inlineCard`
- Card = `blockCard`
- List = `blockCard` with `attrs.datasource`

## Safe update algorithm

1. `getConfluencePage(..., contentFormat="adf")`
2. Locate the exact target node range to mutate.
3. Copy untouched prefix unchanged.
4. Insert replacement nodes.
5. Copy untouched suffix unchanged.
6. `updateConfluencePage(..., contentFormat="adf")`
7. Read the page back in ADF and verify:
   - target nodes changed as intended,
   - untouched regions remain identical,
   - TOC still exists at index 0 for pages governed by this convention.

## Risks / caveats

- HTML body write-back is not reliable for Jira datasource/list patterns; ADF is the safe path.
- Confluence may synthesize storage-format details (for example macro IDs) on write-back.
- Page width remains a separate concern from body ADF in the currently tested tool path.
