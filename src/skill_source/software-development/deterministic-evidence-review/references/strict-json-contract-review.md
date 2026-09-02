# Strict JSON contract verifier review

Use this checklist for validators that parse a machine-readable contract and optionally render a human-readable derivative.

## Core invariant

Malformed input must be rejected through the verifier's normal diagnostic channel. A nonzero process exit caused by an uncaught traceback is not equivalent to controlled fail-closed validation: it can hide the intended error, destabilize CI output, and leave adjacent malformed-input classes untested.

## Type matrix

Probe JSON-native values by semantic class, not only one representative value:

- exact integers: valid integer, equal float (`1` vs `1.0`), boolean, string, list, object, null
- enums/commands: valid string, boolean, integer, list, object, null
- object fields: object, list, scalar, null
- list fields: list, non-empty object, scalar, null
- list items: valid object plus list, scalar, and null items
- nested objects: valid object plus list, scalar, and null

For each malformed case, assert all three:

1. process exits nonzero;
2. output contains the expected validation diagnostic;
3. output contains no traceback or uncaught exception.

Run both the library API and the real CLI. API-only probes can miss failures in rendering, reporting, argument handling, or exit-path code.

## JSON Schema keyword applicability

Many JSON Schema keywords constrain only one instance type. In Draft 2020-12, `pattern` is evaluated only for strings; a non-string value does not fail merely because it cannot match the regex. The same vacuous-success trap applies to other type-specific keywords such as string lengths, numeric bounds, array sizes, and object-property constraints.

For every dynamic schema branch:

1. pair type-specific keywords with an explicit `type` in the same subschema (for example, `{"type": "string", "pattern": "..."}`);
2. inspect every repeated pattern site, including `contains`, conditional, and `$defs` branches—not only the primary property definition;
3. start from a valid document and substitute `null`, number, array, and object values independently;
4. require each substitution to produce a schema error while the untouched document remains valid.

Do not assume an outer `anyOf`, `oneOf`, or `contains` supplies the missing type constraint. A vacuously successful pattern branch can make an otherwise malformed object satisfy both the item definition and the branch-selection rule.

## Validate before ordering, hashing, or rendering

Static model annotations and dataclass field types are not runtime validation. If untrusted values reach deterministic operations first, malformed heterogeneous values can leak implementation exceptions such as `TypeError` during sorting, set construction, regex matching, or canonical serialization.

At the first runtime boundary, validate element types before any operation that assumes comparability or hashability. Raise the documented domain exception, then sort/render only the validated values. Regression tests should call the public construction/publication API and assert the domain exception for `null`, number, array, and object analogues; a bare nonzero exit or generic `TypeError` is not controlled fail-closed behavior.

## Validation-to-render boundary
A common defect is: structural validation appends an error, but execution continues into a renderer that assumes the rejected structure is valid. Typical examples are `item.get(...)` on malformed list items and `nested.get(...)` on a scalar nested object.

Use one of these designs:

- return before rendering whenever structural errors exist; or
- normalize to a typed intermediate representation and render only that; or
- make diagnostic rendering explicitly tolerant of malformed shapes.

Do not use a stale/generated-document comparison as a reason to render an invalid contract.

## Equality and numeric type fidelity

Python equality conflates JSON numbers in cases such as `0 == 0.0` and `1 == 1.0`. It also treats `bool` as an `int` subclass: `False == 0`, `True == 1`, and membership checks such as `False in {-1, 0, 1}` all succeed. Domain, transition, initial-state, and direction checks therefore fail open when they rely on equality or set membership before an exact type check.

For exact JSON type fidelity:

- validate integer fields with `type(value) is int` where booleans, floats, and subclasses are forbidden; perform this check before domain membership, initial-state equality, transition, flip, ordering, or direction logic;
- systematically substitute both `true` and `false` at every numeric field location, including nested `before`, `after`, `direction`, and bias values—not only the first integer field found;
- compare manifests using a representation that preserves JSON numeric spelling/type distinctions, or recursively compare both type and value;
- include nested numeric mismatches, not only top-level fields.

For integrity-indexed evidence packages, a mutation is meaningful only after the changed JSON is canonically rewritten and every dependent artifact identity, manifest entry, and checksum index is regenerated. Invoke the real indexed validator on that internally consistent package. A rejection caused only by a stale checksum does not prove the semantic type guard. Pair each hostile mutation with an untouched positive control, and require the systematic boolean matrix to reject 100% of cases.

Canonical JSON serialization can distinguish integer and float spellings, but document why it is being used and test Unicode, key ordering, and nested values.

## Integration closure ladder

A final focused re-review should include:

1. pin exact HEAD and confirm a clean worktree/index;
2. inspect the narrow remediation diff;
3. rerun the original adversarial matrix;
4. broaden to equivalent malformed containers and nested shapes;
5. verify manifest disagreement and numeric-type mismatches;
6. pair confinement attacks with valid regular-file controls;
7. verify generated output byte-for-byte;
8. run the exact CI command sequence and full suite;
9. repeat HEAD/status/diff checks before verdict.

If the original matrix passes but equivalent nested-container probes still traceback, report the original finding as only partially closed. Ordinarily classify this below a bypass because invalid input still fails, but do not approve a gate whose explicit hardening scope requires controlled malformed-input handling.
