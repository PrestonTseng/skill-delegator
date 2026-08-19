# Confluence Tiny Link Resolution and Blank-Page Fallback

## When this applies

Use this reference when updating a Confluence page from a `/wiki/x/<tiny>` link and the normal MCP `getConfluencePage` tiny-link path fails, or when a target page is effectively blank and an ADF full-body write is unnecessarily large for a concise documentation update.

## Tiny link resolution fallback

Preferred path remains `getConfluencePage(pageId=<numeric page id>, contentFormat="adf")` once the page ID is known.

If `getConfluencePage(pageId="https://.../wiki/x/<tiny>")` or `pageId="<tiny>"` fails with an auth/scope or parameter error but the page is otherwise accessible, resolve the numeric ID before giving up:

1. Try Rovo/CQL search if the title or nearby content is known.
2. If search cannot identify the page and the tiny token is a classic Confluence tiny link, decode it:
   - Confluence tiny links are generated from a 32-bit little-endian page ID.
   - Encode algorithm: `base64(pack('<L', pageId))`, remove `=`, map `/ -> -`, `+ -> _`, and apply Atlassian's padding-related `A` handling.
   - Reverse algorithm may require trying insertion of the omitted `A` before base64 decoding. Validate by re-encoding the candidate page ID and confirming it exactly reproduces the tiny token.
3. Read the numeric page ID in ADF and continue normal surgical-update workflow.
4. Record the resolved page ID in the work log/final report.

Minimal Python decoder pattern:

```python
import base64, struct

def tiny(n):
    s = base64.b64encode(struct.pack('<L', n)).decode()
    out = ''
    padding = 0
    for c in s:
        if c == '=':
            continue
        if padding == 1 and c == 'A':
            continue
        padding = 0
        out += {'/': '-', '+': '_', '\n': '/'}.get(c, c)
    return out

def candidates(token):
    for pos in range(len(token) + 1):
        cand = token[:pos] + 'A' + token[pos:]
        raw = cand.replace('-', '/').replace('_', '+')
        try:
            b = base64.b64decode(raw + '==')
        except Exception:
            continue
        if len(b) == 4:
            page_id = struct.unpack('<L', b)[0]
            if tiny(page_id) == token:
                yield page_id
```

## Blank-page Markdown fallback

ADF remains the default for governed Lilee pages. However, if all of the following are true, a Markdown write is acceptable as an explicit exception:

- the target page is blank or effectively blank, so there is no meaningful untouched ADF to preserve;
- the content is a concise explanatory/reference document, not a Jira datasource, smart-link-heavy page, release note, delivery map, KPI page, or structured governed template;
- an ADF draft was still generated or the intended structure was otherwise validated before write-back;
- the final report clearly says Markdown fallback was used and why;
- the page is read back after write to verify the expected sections and representative values persisted.

Do not use this exception for surgical edits to non-blank pages. Do not claim TOC-first or status-control compliance if the Markdown write path did not preserve those ADF nodes.