# Bulletin location semantic review

Use this when a Gerrit patch validates bulletin `Line` / `Track`, signal endpoints, or manual milepost ranges.

## Contract checks

1. **Separate identity from display text.** If the authoritative static schema says a Line has ID `T3` and display name `Main`, do not accept an enum whose serialized value is `Main` merely because the UI label looks correct. Trace the serialized value through REST, GraphQL, persisted bulletin fields, signal ownership, and downstream requests.
2. **Treat each endpoint as one location choice.** A From/To endpoint that accepts a signal ID *or* custom milepost must not silently accept conflicting dual representations. If the transport intentionally carries resolved mileposts plus signal IDs for audit, distinguish the public input contract from the resolved downstream contract.
3. **Trace precedence, not only validation.** Find the resolver that chooses between `signal_id` and `milepost`. If it prefers the manual milepost but forwards both fields, require either mixed-input rejection or equality between each signal's configured milepost and the supplied manual value.
4. **Validate the pair as a pair.** Checking each signal's Line, Track, and Direction independently does not prove that start/end ordering, range shape, or the resulting segment is valid. Compare the resolved endpoint pair against direction and range requirements.
5. **Review interval coverage semantically.** Normalize reversed block endpoints before range coverage, but do not confuse scalar milepost overlap with physical connectivity when topology can branch. Confirm whether “adjacent” means shared topology vertex or merely equal/overlapping milepost coordinates.
6. **Check ownership invariants.** Deriving Line/Track discovery from block records is safe only if duplicate, missing, unknown, and cross-track physical-block ownership cannot silently produce multiple valid scopes.

## Form and UI checks

- Numeric Angular controls need numeric validators. `Validators.minLength` / `maxLength` do not constrain number values, so explicitly require integer kilometer/meter parts and numeric bounds (normally meter `0..999`). Probe overflow, negative, and fractional values. Compare the text shown in the form/confirmation with the normalized milepost sent and later rendered; accepting `1k+1000` while persisting/rendering `2k+000` creates operator ambiguity even when both denote the same scalar position.
- `FormGroup.enable()` recursively enables disabled children. When Track is intended to depend on Line, check initial state and every range-mode switch; enabling the active range group can accidentally expose an enabled-but-empty Track selector before Line is chosen. Restore dependent-child state explicitly and test it.
- Treat Line/Track E2E expectations as independent scenario data. Do not let a shared helper silently select the first Line or hard-code a Track while assertions omit both fields. Parameterize the expected Line identity/display and Track, then verify the persisted table and reopened editor. Include an alternate Track plus an invalid/stale Line–Track pair edge case.

## Deterministic probes

- Construct a request whose signal pair and manual milepost pair are each independently valid but describe different sections. Call the validator directly; acceptance demonstrates ambiguous targeting.
- Extract the configured signal mileposts and compare them with the resolver-selected output values and the downstream serialized payload.
- Print or assert `(line.id, line.display_name)` separately; a test that expects the same source value for both can accidentally freeze an identity/display conflation.
- For interval merging, include disconnected blocks with touching or overlapping milepost coordinates and decide from the authoritative topology contract whether they should merge.
- For Angular number fields, instantiate the real control validators and print validity/errors for canonical, overflow, negative, and fractional values; do not infer HTML `type="number"` or length validators enforce the required domain.
- For dependent dropdowns, inspect control state immediately after form connection and after switching range modes, before setting Line.

## Read-only Python verification

When project sync is blocked by a private dependency, use `uv run --isolated --no-project` with only public dependencies and temporary stubs outside the checkout for the narrow imported symbols. Set `PYTHONPATH` explicitly to the checkout's `src` plus the temporary stub root. Remove the stub root afterward and verify both `git status --short` and absence of an accidentally created `.venv` before reporting. Do not persist environment-specific dependency failures as review conclusions.
