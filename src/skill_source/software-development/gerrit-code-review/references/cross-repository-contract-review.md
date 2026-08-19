# Cross-repository Gerrit contract review

Use this when two or more Gerrit changes implement one behavior across producer, gateway, API, and UI-facing repositories.

## Review sequence

1. Record every change number, patch-set number, exact revision SHA, parent SHA, status, CI vote, and upload timestamp.
2. Discover companion changes even when the review request names only one repository. Search Gerrit by Jira family, distinctive contract symbols/subject wording, owning project, and the consumer patch's upload window. A producer change may use a different Jira key while still defining the reviewed consumer contract.
3. Read the authoritative behavioral source before accepting an implementation-plan shortcut. Capture exact required operator timing, warning/blocking semantics, field names, units, and ownership granularity.
4. Fetch every exact patch set locally. Do not compare one repository at a branch tip while reviewing another at a patch ref. For historical consumer patch sets, pin the producer revision that existed when the consumer patch was uploaded; separately inspect the producer's current revision only to identify later fixes. This prevents a future producer patch from making an older consumer look compatible retroactively.
5. Build an end-to-end contract trace:
   - source/config model;
   - runtime validation;
   - mutation ordering;
   - service response schema;
   - gateway/client deserialization;
   - public API/GraphQL schema;
   - UI-consumable signal;
   - tests at each boundary.
   For broad terminology renames, inventory occurrences by **GraphQL object/input and runtime domain**, not just by spelling. The same legacy field name may exist in static TrackMap, bulletin, signal, and realtime telemetry contracts with different producers and rollout schedules. Validate every changed client operation against the temporally appropriate exact producer schema; do not let a correct rename in one object justify renaming an unrelated subscription field.
6. Map linked parent/sibling tickets to release order. Distinguish:
   - a defect introduced by the reviewed patch;
   - an intentionally incomplete sibling-ticket dependency;
   - an atomic cross-repository rollout requirement.
   Report a directly broken current operation as a finding. Report a missing field owned by a clearly identified pending sibling ticket as release-order context unless the reviewed patch claims independent releasability.
7. Compare the current patch set with prior patch sets when multiple revisions exist. Look for deleted response wrappers, warning models, transport fields, and end-to-end tests; deletion can turn a visible operator workflow into log-only behavior while all current tests stay green.
8. Distinguish computation from delivery. Producing a warning internally is insufficient when the requirement says an operator must see and confirm it before mutation.
9. Verify ordering explicitly. For confirmation-gated actions, assert that state, timers, persistence, and notifications remain unchanged before confirmation, then change only after confirmation.
10. Compare duplicated static datasets programmatically by stable key and all contract fields. Report current equality separately from the architectural risk of future drift.
11. Run each repository's full feasible suite and a cross-contract probe. Green independent suites do not close a source-contract mismatch. A frontend build and mocked/component tests also do not validate GraphQL field existence; schema validation or exact producer-schema inspection is required.

## Finding pattern

For a cross-repository contract defect, cite all broken hops rather than only the first producer line:

- authoritative requirement quote;
- producer mutation/validation lines;
- service response schema;
- gateway/client model;
- public API resolver/schema;
- deleted prior-patch implementation or tests, when relevant;
- user-visible impact;
- fix direction and required ordering test.

## Common pitfalls

- Treating an assignee-authored implementation plan as authority when it weakens the live behavioral spec.
- Calling post-mutation audit logs a non-blocking confirmation flow.
- Restoring a warning in a successful mutation response even though the requirement needs confirmation before mutation.
- Accepting unitless public names such as `maxSpeed` when the source contract requires an explicit unit-bearing field such as `maxSpeedKmh`.
- Silently changing ownership from per-block to per-sub-block without an accepted source update.
- Reporting separately green repositories as proof of end-to-end compatibility.
