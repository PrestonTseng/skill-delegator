# Multi-source KPI refresh recipe

## Structural extraction

For each Delivery Map, walk top-level headings and associate each workstream heading with the first table before the next heading. Extract columns by header name rather than fixed position:

- `Work Item`
- `Function`
- `Assignee`
- `Ticket`
- `Due Date`
- optionally `Deliverable / Done When`

Read Story Ticket and workstream goal from the paragraphs between heading and table. Preserve source `mention` IDs and Jira `inlineCard` URLs.

## Due-date resolution

Resolve only supported, source-backed expressions:

- explicit ISO or slash date;
- `YYYY-MM-DD + nD`;
- `WSx.y + nD`;
- rendered `expression = YYYY-MM-DD` (use the rendered RHS);
- `max(WSa.b, WSc.d) + nD` when every dependency resolves.

Treat `D` as Mon–Fri business days unless the source declares otherwise. Do not skip holidays without an explicit calendar.

Keep these cases distinct in KPI compact lines:

- `skip` → `Due skipped`
- unresolved nonblank expression → `Due: <expression>`
- blank source → `Due TBD`
- resolved date → native ADF `date`

## Release derivation

1. Use an explicit Delivery Map status as authoritative.
2. If no status exists, map the latest resolved work-item date to the target KPI's explicit release window.
3. If no date resolves, use `Target TBD`.
4. Never override explicit `Target TBD` or `Product Refinement` with a derived release.
5. Exclude non-release statuses from committed release-wave rollups.

## Large-page REST write-back

- Fetch target with `body-format=atlas_doc_format`.
- Save before body and candidate body.
- Mask only governed top-level sections and compare the rest exactly.
- Re-fetch immediately before PUT; abort on drift.
- PUT the full ADF body with incremented page version.
- Read back and save the persisted ADF.

## Round-trip semantic comparison

Confluence commonly:

- adds `localId` to newly authored nodes;
- adds or refreshes `__confluenceMetadata`;
- merges adjacent text nodes with identical marks;
- removes empty `content: []` from empty paragraphs.

Normalize only those four renderer differences before comparing candidate and read-back. Any change to node type, status text/color, link URL, mention ID, date timestamp, list order, or feature content is substantive and must fail verification.

## Jira schedule gaps

Fetch Jira with field names/schema when possible. Standard examples:

- Start date may be a custom field.
- Due date is commonly `duedate`.

If Start date exists but Due date or assignee is null, show the exact known Start date plus explicit `Due date not set` / `Assignee not set`. Do not infer from sprint, release window, issue history, or user expectation.
