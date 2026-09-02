# Closed-Bar Indicator Chain Review

Use this reference when reviewing deterministic trading-indicator plugins that compose closed-bar observations into later gates, risk levels, or decisions. The goal is semantic correctness and causal ordering, not chart rendering.

## Authority Split

Pin three authorities separately:

1. **Formula authority:** exact source bytes and locators for pivots, thresholds, traversal, mitigation, and event transitions.
2. **Strategy authority:** which source-valid parameters and plugin chain are active.
3. **Runtime contract:** `PASS`/`FAIL`/`UNAVAILABLE`, identity fields, `event_time`, `known_time`, dependency IDs, exact numeric types, and closed-bar/no-lookahead rules.

Do not require the source platform or UI when static source plus deterministic Python probes can close the product claim. Do not let synthetic fixtures masquerade as source parity; they prove the translated contract only after source locators are pinned.

## Four High-Value Adversarial Seams

### 1. Dependency status algebra

For every dependent plugin, supply an otherwise-valid prerequisite with each status:

| Prerequisite | Required downstream behavior |
|---|---|
| `PASS` | Evaluate normally |
| `FAIL` | Deterministic downstream `FAIL`; never `PASS` |
| `UNAVAILABLE` | Downstream `UNAVAILABLE` unless the binding contract says otherwise |
| Missing, wrong identity, future-known, contradictory direction | Fail closed with the contract's exact status |

Test every consumer of the shared dependency helper. Two passing examples do not prove the shared seam is safe.

### 2. First-observation freezing

When a zone becomes fully traversed, freeze the actual first traversal bar's directional extreme:

- buyside sweep: traversal candle `high`;
- sellside sweep: traversal candle `low`.

Do not substitute the static zone boundary. Append later, more-extreme bars and prove the frozen value and earlier observation bytes do not change. Verify the risk plugin consumes that frozen value.

### 3. Point-in-time composition

Name the strict causal inequality before testing. For a liquidity-sweep-then-FVG chain:

```text
liquidity.known_time < fvg.known_time
```

Probe forward, reversed, and equal-time/same-bar cases. Equal time must have an explicit policy; conservative closed-bar composition should fail closed unless the authority defines a deterministic same-bar order. Check compatible dependency-chain identity as well as direction and status, because two independently valid observations can still belong to unrelated chains.

### 4. Source parameter shape

Distinguish parameters that look similar but occupy different roles. For pivot functions, configurable left width and fixed right confirmation width are separate values. Translate source input domains exactly, including derived forms: if a source input `m` ranges from 2 through 7 and the implementation stores `m / 10`, the representable domain is the exact tenths 0.2 through 0.7—not every Decimal inside that interval.

Probe defaults, both bounds, one step outside each bound, non-step values, and Python's boolean-as-integer trap. Require `type(value) is int` where exact integer identity is binding.

## Review Matrix

- Warm-up and first knowable bar
- Bullish/bearish symmetry
- BOS/CHoCH or MSS/BOS transition state
- Uncrossed-pivot and close-crossing rules
- Equality threshold exact boundary and one tick outside
- Traversal/mitigation exact boundary
- Dependency `PASS`/`FAIL`/`UNAVAILABLE` matrix for every consumer
- Forward/reversed/equal-time chain
- Prefix invariance after appending future bars
- First-traversal extreme freeze and no rewrite
- Two-run canonical replay byte identity
- Production registry/config loading with source-valid defaults and bounds
- Full suite, type/lint/build/fresh install, package source-leak scan

## Verdict Discipline

A green full suite, deterministic replay, and clean package can coexist with semantic fail-open defects. Keep ordinary quality gates separate from formula/state/temporal approval. Any failed dependency accepted as `PASS`, wrong frozen extreme, reversed causal chain, lookahead, or source-invalid active parameter is blocking until an independent adversarial probe closes it.
