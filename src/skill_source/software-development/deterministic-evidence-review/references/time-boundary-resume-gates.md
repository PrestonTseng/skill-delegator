# Time-Boundary Resume-Gate Proof Matrix

Use this reference for independent review of fixes that decide whether a successor interval/bar is due at a scheduler cutoff.

## Contract matrix

| Region | Example relation | Required behavior |
|---|---|---|
| Before close/due | `successor_open + frame > canonical_cutoff` | Retain prior state; publish no transition; emit no missing-history error. |
| Exact close/due | `successor_open + frame == canonical_cutoff` | Successor is due. Missing first successor or discontinuity fails closed. |
| After close/due | `successor_open + frame < canonical_cutoff` | Resolve from complete contiguous evidence or fail closed. |

Also test aligned and off-grid event timestamps. Derive the first successor using epoch alignment, not scheduler invocation time.

## Independent RED recipe

Use a disposable archive so the source worktree remains untouched:

```bash
TMP="$(mktemp -d)"
git archive <base> | tar -x -C "$TMP"
cp <candidate-test-file> "$TMP/<test-path>"
(
  cd "$TMP"
  PYTHONDONTWRITEBYTECODE=1 <test-command> <pre-close-test> <exact-close-control>
)
```

A valid RED is one behavioral failure at the intended production boundary. The exact-close control should pass when existing fail-closed logic was already correct. Remove the temporary tree afterward.

## Source trace checklist

- Where is the canonical cutoff normalized?
- Is fractional precision intentionally preserved or truncated?
- Does the changed helper receive that exact cutoff?
- Does the branch reference wall clock, start/completion time, evaluation time, or retrieval time? If yes, justify it against the contract.
- Are candidate bars independently constrained to closed evidence at or before the same cutoff?
- At equality, does strict comparison route into existing missing/misaligned/discontinuous checks?
- Does deferral preserve append-only prior state without writing a synthetic duplicate OPEN transition?

## Immutable natural-evidence checklist

For the incident and first subsequent publication, directly verify:

- manifest `as_of`, started/completed/evaluation times, status, artifact hashes;
- latest available predecessor/successor open and close timestamps;
- blocker codes and empty/non-empty transition files;
- originating signal timestamp and canonical first geometry;
- state reconstruction, order count, OPEN/RESOLVED status, and exact cash reconciliation;
- daily aggregate's actual schema, supporting verified count, in-window count, exposure, duplicates, and resolutions;
- evidence-tree file count and deterministic digest before and after all read-only probes.

If a checker raises `KeyError` or an attribute error, inspect the real schema/dataclass before classifying the product. A guessed probe field is not product evidence.

## Packaged-diff verification

A review package may use wider unified context than default `git diff`. Compare hunk headers and lengths, then try the recorded/likely rendering such as:

```bash
git diff --unified=10 <base>...HEAD
```

Alternatively prove reverse applicability. Do not call the package stale solely because default three-line context differs byte-for-byte.

## Decision shape

A resume approval should state:

1. exact reviewed range and HEAD;
2. separate Spec, Quality, and Integrity verdicts;
3. fresh RED/GREEN, focused/full, compile/build, wrapper, and diff evidence;
4. direct immutable incident and subsequent-run facts;
5. authorization boundaries and prohibited actions not taken;
6. one controlled trigger, then first natural proof, with read-only reconciliation after each;
7. explicit pause conditions;
8. whether code-gate approval closes only review or also the incident (normally the latter waits for natural branch exercise).
