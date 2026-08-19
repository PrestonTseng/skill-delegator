# Safety-Critical Code Generation Plan Review

Use this reference when planning or grilling generated PLC/control logic, safety-adjacent simulators, or other code generators whose outputs drive externally visible state.

## 1. Separate evidence from invented behavior

Before planning timers, release rules, proof conditions, or fallback behavior, identify the independent input that can actually prove each condition.

- A timer without an engineering value is a simulator guess, not a requirement.
- A “proved” state derived only from values the same scan just assigned is tautological.
- Release/order logic reconstructed from legacy code is semantic reverse engineering, not mechanical migration.
- When engineering is absent, model the field/capability as explicitly `incomplete` with provenance and block executable generation. Omit it or label it unsupported only when the product scope truly excludes it. Never use an empty collection or zero timeout to mean “unknown,” and never emit a plausible-looking implementation.

For a planned capability with incomplete site data, separate draft validation from executable-target validation: the draft loader may produce a review matrix, while ST/runtime generation fails until every safety-critical field is reviewed and confirmed.

## 2. Make proof scope explicit

Name what `PROVED`, `COMPLETE`, `READY`, or equivalent actually proves:

- internal software state readback;
- external device feedback;
- physical correspondence;
- full safety/interlocking conditions.

If only internal outputs are available, expose a scope such as `simulator_internal` and list excluded protections per operation/entity. Never let a consumer infer physical proof from an internal acknowledgement.

For external feedback, do not accept a static `FRESH=true` bit as proof of liveness: a communication failure can freeze the last-good value indefinitely. Prefer an external heartbeat/generation counter, require at least one observed change before declaring feedback fresh, and let the PLC derive STALE after a separately reviewed interval without further change. Treat counter wrap as movement, not failure. Point movement timeout, signal proving timeout, feedback stale interval, route-entry expiry, and release clear-hold are different engineering fields; never reuse one generic timeout.

## 3. Review the canonical model for real immutability

`frozen=True` is shallow when nested lists/dicts remain mutable.

- Use tuples for ordered collections.
- Use immutable/keyed indexes such as `MappingProxyType` in a frozen aggregate.
- Test nested append and index assignment failures.
- Define every document root, field, type, unit, optionality, default, enum, and cross-document constraint. A plan that specifies only representative models forces implementers to invent the contract.
- Provide stable diagnostics: code, document, field path, line/column, and message.

## 4. Treat legacy behavior migration as a reviewable decision

Counts and IDs can be migrated mechanically; route resources, conflicts, proof predicates, lock ownership, release conditions, and aspects usually cannot.

A practical gate:

1. Reconstruct every semantic record with exact source locators.
2. Emit a naturally sorted review matrix outside the product repository.
3. Canonicalize and hash the reviewed records.
4. Require human approval of the matrix/hash before behavior generation.
5. Add the approved fingerprint to a test so later edits cannot silently change the reviewed oracle.

Do not use the newly written canonical file as its own unreviewed oracle.

## 5. Prove target-specific mappings on the exact runtime

Source inspection is evidence, not final confirmation of a deployed image.

Before freezing register/address contracts:

1. Compile a one-word minimal program on the exact image/toolchain.
2. Write/read the expected external protocol address.
3. Verify neighboring/alternative addressing assumptions do not alias.
4. Restart and record persistence/initialization behavior.
5. Capture image digest, protocol function/address, values, compiler logs, and health.
6. Mark the mapping confirmed only after the probe passes. Before then, publish any review representation with explicit `addressing_status: incomplete` and a null/absent image digest; executable-target validation and tracked runtime artifacts remain blocked. Use a standalone probe fixture so the unconfirmed canonical artifact is not treated as its own evidence.

Keep this probe temporary or in plan evidence unless it has continuing product value.

## 6. Design command framing against torn writes and replay

For a multi-word command over Modbus-like protocols:

- Define one producer and single- vs multi-in-flight policy.
- Commit payload plus strobe/version in one atomic protocol request when possible (for example FC16).
- Snapshot only on a low-to-high armed edge.
- Require the strobe to return low before re-arm.
- Define exact sequence progression and wrap behavior.
- Define stale/replayed/out-of-order handling without changing shared outputs.
- On startup, acknowledge/de-arm retained words without executing them.

Black-box tests should exercise no-edge payload writes, replay, wrap, restart de-replay, and correlation.

## 7. Eliminate last-writer-wins shared outputs

Per-route generated sections must not each assign shared signals, locks, authority, or direction outputs.

Use a deterministic scan shape:

1. restrictive first-scan guard;
2. input/prior-output snapshot;
3. command-edge snapshot;
4. route next-state/resource request evaluation;
5. centralized owner commit;
6. centralized output derivation.

Represent shared resources with an owner (`0`/none or operation ID) and test that each shared output has exactly one central writer. Define arbitration and conflict precedence explicitly.

## 8. Fail closed during active operation

Validation only at request time is insufficient.

- Normalize inputs every scan.
- Only an exact permissive encoding is permissive.
- UNKNOWN, invalid, absent, or communication-anomalous values are restrictive.
- Define the active-state transition: stop/remove permission immediately, retain protective ownership, and enter a held/fault state.
- Do not automatically re-clear after uncertainty unless independent evidence and reviewed semantics justify it.
- Distinguish “cancel is restrictive” from “all protected resources are released.”

## 9. Test semantics, not only generated strings

A strong stack combines:

- typed semantic IR/state-table tests;
- renderer/binding parity and single-writer checks;
- exact toolchain compile/start;
- black-box protocol scenarios;
- externally orchestrated restart tests.

Substring assertions alone prove text presence, not behavior. Pytest should not restart the container it is currently using; perform restart in the shell/orchestrator between a prepare test and a verification test.

## 10. Keep the public build contract atomic

Do not expose a partially complete `build` command in an intermediate checkpoint.

- Render every output first.
- Stage and fsync all outputs.
- Replace as a group.
- Inject failure on the second replacement and prove rollback restores all originals.
- Run CLI tests only in a complete temporary project, never against tracked repository outputs.

## 11. Reopen approval when review changes the approved design

Reviewer feedback is not user approval. If a grill removes behavior, changes proof scope, changes fail-safe transitions, or otherwise materially differs from the approved design:

1. Incorporate the technically validated findings into a reviewable plan.
2. Mark the plan non-executable behind a re-approval gate.
3. Do not silently rewrite the accepted design as though the user already approved the delta.
4. Explain each delta in plain language: what the system knows, what it cannot know, conservative behavior, benefit, and operational cost.
5. Use concrete analogies for non-specialists and make a recommendation without hiding the trade-off.
6. After approval, update the design record and begin implementation.
