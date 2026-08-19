# Delivery Map due refresh: product-refinement skip pattern

Use this when recalculating Delivery Map due dates / release labels and some stories or workstreams have been moved to Product Refinement.

## Rule

- Treat a workstream whose heading contains a `product refinement` status/text label as frozen for the refresh pass.
- Do not recompute its work-item due-date cells.
- Do not derive or replace its release status.
- Preserve the heading label exactly, e.g. `product refinement` rather than replacing it with `SafeART X`.

## Dependency handling

A non-product workstream can still depend on a row whose formula cannot be fully resolved because a predecessor due date is blank.

When that happens:

1. Do not fail the entire refresh if the cell already has a rendered RHS date in the form `expr = YYYY-MM-DD`.
2. Use the existing rendered RHS date as a fallback for release-label derivation.
3. Leave that due-date cell unchanged.
4. Record the fallback explicitly in the task artifacts / final report.

Example:

- `WS10.4 = max(WS10.1, WS10.3) + 5D = 2026-09-11`
- If `WS10.1` is blank, keep `2026-09-11` as the rendered fallback and do not rewrite the cell.

## Verification

After write-back:

- Re-run the refresh against read-back ADF; expected remaining due/release changes should be zero.
- Confirm product-refinement headings are still product-refinement headings.
- Confirm changed release labels are still ADF `status` nodes.
- Confirm changed tables preserved table attrs such as width and localId.
- Report any fallback formulas separately from normal recalculated cells.
