# Hostile-State Planning Probes

Use this when reviewing a read-only scanner/planner that may later authorize filesystem mutations.

## 1. Path-prefix matrix

Do not test only the final target component. Build temporary fixtures for:

| Ancestors | Final leaf | Required result |
|---|---|---|
| all real directories | absent | safe empty state |
| all real directories | real directory | scan normally |
| symlink ancestor | absent | blocked |
| symlink ancestor | existing directory | blocked before traversal |
| regular-file ancestor | absent | blocked |
| exact target symlink, including dangling | any | blocked |

A common fail-open shape is:

```python
root = abspath(target)
if not lexists(root):
    return EMPTY
lstat(root)
```

`lexists(root)` says nothing about why the exact leaf is unreachable, and `lstat(root)` still follows symlinks in earlier components. Walk from the filesystem anchor through every existing component with `lstat`; the first missing component is acceptable only when every prior component was a real directory.

Pair scanner probes with the real planner/CLI. An unsafe prefix must produce the documented blocked exit and no `CREATE`, `REPLACE`, or `REMOVE` operations. Snapshot entry kinds, file bytes, and raw link targets before/after to prove zero mutation.

## 2. Schema/parser differential

When a JSON Schema and handwritten parser describe the same manager-owned metadata:

1. Start from one valid ownership document and a valid filesystem control.
2. Mutate exactly one schema constraint at a time: unknown/missing keys, duplicate keys, scalar types, canonical IDs, path strings, digest format, owner marker, and schema version.
3. Run the document through both `Draft202012Validator.iter_errors()` and the production parser.
4. Require this invariant: **schema-invalid must never become manager-owned**.
5. Exercise at least one accepted-invalid identity through planning; confirm it cannot authorize `REMOVE`.

Pay special attention to copied canonical-ID logic. A confinement-only parser may accept leading-dot segments, backslashes, controls, or characters rejected by the published schema. This is parser/schema drift, not merely stricter-versus-looser validation, when acceptance grants ownership authority.

## 3. Reporting

Report path-prefix acceptance and schema/parser drift separately. Include exact source lines, fixture construction, actual output, blocked/mutation state, and independent Spec/Quality verdicts. Do not treat a green happy-path suite as evidence for these boundaries.
