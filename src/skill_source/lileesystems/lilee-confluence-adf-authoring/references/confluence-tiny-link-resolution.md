# Confluence tiny-link resolution

Use this when a user gives a Confluence short URL such as:

```text
https://<site>.atlassian.net/wiki/x/<token>
/wiki/x/<token>
<token>
```

and `getConfluencePage(..., pageId=<token or full URL>)` rejects the token, treats it as a non-numeric ID, or returns an auth/scope error that appears specific to short-link resolution rather than the target page itself.

## Deterministic decode workflow

Confluence tiny-link tokens encode the numeric page/content ID in little-endian bytes with Confluence's nonstandard URL-safe Base64 substitutions.

Decode algorithm:

```python
import base64

def confluence_tiny_to_page_id(token: str) -> int:
    token = token.rstrip('/').split('/')[-1]
    b64 = token.replace('-', '/').replace('_', '+').ljust(8, 'A')
    return int.from_bytes(base64.b64decode(b64.encode()), byteorder='little')
```

Example from a live session:

```python
confluence_tiny_to_page_id('AoCK5')  # 3834281986
```

Then read the page by numeric ID:

```python
mcp_atlassian_getConfluencePage(
    cloudId='lileesystems.atlassian.net',
    pageId='3834281986',
    contentFormat='adf',
)
```

## Verification discipline

After decoding:

1. Read the numeric page ID in ADF.
2. Verify the returned title/space/parent matches the intended target.
3. Record the resolved page ID in the work log or final report.
4. If the decoded page is inaccessible or clearly wrong, fall back to Rovo/CQL search by expected title or nearby source terms.

## Notes

- Confluence uses `/ -> -` and `+ -> _`, which is the reverse of standard RFC 4648 URL-safe Base64 substitutions.
- Padding is restored by left-justifying the token to length 8 with `A` before Base64 decoding.
- This is a resolution technique, not a reason to avoid MCP. Once the numeric page ID is known, continue the normal ADF read/update/read-back workflow.
