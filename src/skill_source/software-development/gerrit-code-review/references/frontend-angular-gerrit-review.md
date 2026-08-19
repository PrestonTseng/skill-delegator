# Frontend Angular / Nx Gerrit review notes

Use this reference when a Gerrit patch changes Angular/Nx frontend code, especially components, templates, pipes, GraphQL documents/services, i18n assets, or Apollo client usage.

## Verification pattern

Prefer a layered verification set:

```bash
npm ci
npx nx test <project> --testFile=<changed-component-or-service.spec.ts> --runInBand
npx nx test <project> --testPathPattern='<changed-area-or-pipes-regex>' --runInBand
npx nx build <project> --configuration=development
npx nx lint <project>
npx nx test <project> --runInBand
```

Notes:
- `--testFile` accepts one string in this repo shape. For multiple specs, use the singular Jest option `--testPathPattern` with a regex instead of repeating `--testFile`.
- Do not use `--testPathPatterns` (plural) here: Nx/Jest may ignore it and silently run the full project suite. Always verify the reported suite names/count match the intended focused selection; an exit code alone does not prove the filter applied.
- Full `nx test` may emit existing console errors or warnings while still passing; report them as observed noise unless they are introduced by the reviewed patch.
- `nx lint` may pass with warnings. Distinguish `0 errors` from existing warnings.

## Review heuristics

- For Apollo GraphQL changes, review the client routing as well as the GraphQL document. If a method is a normal query, check whether it should use the default HTTP client (`apollo.query` / `watchQuery`) or a websocket/named client (`apollo.use('...').subscribe`). Do not assume `apollo.subscribe` is appropriate just because nearby realtime subscriptions use it.
- If a patch adds GraphQL service methods, check whether service tests verify the actual operation document and selected Apollo client. Component tests with a mocked service do not cover document names, fields, variables, or default-vs-named client usage.
- For pipes that convert unknown enum values to user-facing text, distinguish between truly unknown values and disconnected / missing data. If the patch changes `unknown` to `disconnected`, look for tests that cover both valid enum values and null/undefined/missing state.
- For template changes that add null guards before Angular pipes/classes, verify both build/type-checking and a focused component test covering initial state before async data arrives.
- For i18n key renames, search for the old key and run tests that exercise the affected pipes/components.

## Reporting

When Jira/Confluence cannot be read but Gerrit REST and local checkout are available, explicitly label the limitation: code behavior and verification can be reviewed, but requirement-completeness claims are limited without the source ticket/spec.
