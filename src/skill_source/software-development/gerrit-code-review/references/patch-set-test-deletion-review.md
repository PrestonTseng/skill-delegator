# Patch-set test-deletion review

Use this when the newer Gerrit patch set changes only tests, especially when it removes cross-repository or API-contract tests.

## Review method

1. Diff the exact previous/current revisions and confirm whether production code is unchanged. Classify findings as **behavior regression**, **evidence regression**, or **pre-existing coverage gap**; do not conflate them.
2. Read every removed test from the previous revision. Record what contract it uniquely exercised, whether it ran by default or was environment-gated, and whether equivalent coverage remains elsewhere.
3. Map surviving tests by layer:
   - SDL/schema-string assertions prove field presence only.
   - Service tests prove domain projection only.
   - Dependency overrides prove framework wiring invoked the override, not the real dependency's accept/reject behavior.
   - Resolver/handler execution proves glue and serialization.
   - Consumer-operation validation proves cross-repository compatibility.
4. For breaking GraphQL renames, validate real consumer operation documents against the exact producer schema. Report each rejected field and pin the consumer revision used. A green producer suite cannot establish consumer compatibility.
5. Check that any removed cross-repository test is itself viable: extraction regexes still match the consumer source shape, named operations still exist, referenced helper paths exist, and CI actually supplies the required repository/env variable. If stale, request a repaired/replaced gate rather than blindly restoring it.
6. Ground completeness in the requirement's normal-path and edge-case bullets. New API fields should generally have an execution-level normal test and a validation/error edge test; schema text plus service tests can both pass while resolver glue is broken.
7. Run focused changed-area tests and the full supported suite when feasible, then reconfirm exact HEAD and clean checkout.

## Calibration

- Report a production regression only when executable evidence shows behavior changed between patch sets.
- A removed unique compatibility gate is usually a Medium evidence regression when the patch intentionally breaks a public contract.
- Missing resolver execution for a newly introduced API is a core coverage gap when only schema and service layers are tested.
- Removal of a test for unchanged shared infrastructure is not automatically core. For example, an endpoint test that overrides authentication plus deletion of a generic authentication unit test loses negative-branch coverage, but severity depends on whether authentication is part of the change's stated acceptance contract.

## Reporting

Include the deleted previous-patch path/line range, surviving current-patch coverage, the exact producer and consumer revisions used for probes, and a replacement-test direction. Scope compatibility claims to the consumer revision actually inspected; do not imply all coordinated changes are broken when only current main/master was tested.
