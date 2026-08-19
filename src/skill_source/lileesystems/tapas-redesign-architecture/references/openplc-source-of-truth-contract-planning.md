# OpenPLC Source-of-Truth Contract Planning

Use this reference when a TAPAS redesign change compiles canonical human-reviewed data into runtime JSON, JSON Schema, and OpenPLC Structured Text.

## 1. KISS contract shape

- Load a fixed, small authored YAML bundle into one deeply immutable, cross-validated project model.
- Feed JSON, schema, ST, review matrices, and UI metadata from that same resolved object. Generators must not reload YAML independently.
- Track deterministic JSON/ST at stable paths when consumers pin repository tags; make the check path compare bytes without rewriting.
- Keep one-time migration/review tools and runtime evidence outside the product surface unless they have continuing maintenance value.
- Do not pre-create frontend/backend/Compose/profile/tooling trees for later phases.
- Do not start implementation until the reviewed plan and any newly surfaced safety clarifications are explicitly approved.

## 2. Missing engineering is data, not absence

When approved behavior requires points, detection, proof, overlap, flank protection, entry/approach detection, or ordered release, put those fields in the canonical route schema immediately.

Use a wrapper such as:

```text
state: confirmed | provisional | incomplete | not_applicable
value: ... | null
source_refs: [...]
unresolved_question: ... | null
responsible_party: ... | null
note: ... | null
```

Rules:

- `incomplete`: no value; exact unresolved question and responsible party required.
- `confirmed`: value and reviewed provenance required; a confirmed empty list means “reviewed and none required.”
- `not_applicable`: only for fields explicitly allowed to be inapplicable; requires reason/provenance.
- Never encode unknown as `[]`, zero, healthy, clear, or an omitted key.
- Draft models may render review JSON and a 34-route review matrix, but executable ST generation is blocked until every required safety field is confirmed.
- Fingerprint the reviewed normalized route matrix and stop for explicit approval before behavior generation.

Do not use a generic `unsupported_categories` escape hatch when the approved behavior already requires that category's schema. That pattern is suitable only when the capability itself is deliberately outside the selected profile.

## 3. Route contract and exact release ownership

An executable route should explicitly carry:

- from/to signals;
- ordered blocks and sub-blocks;
- direction and non-zero numeric owner/target code;
- required points and positions;
- required-clear, entry, and approach detection;
- independent proof predicates;
- conflicts, overlap, and flank protection;
- named timing policies;
- ordered sectional release steps; and
- an explicit final-release partition.

Validate that every acquired resource appears exactly once in a sectional step or final release. Renderer-implied cleanup is not a reviewable release contract.

Each sectional step requires its detector to be observed `OCCUPIED`, then healthy/fresh `CLEAR` continuously for its reviewed hold interval. Unknown, stale, unhealthy, out-of-order, or missing observations retain ownership. Unlocking a point clears ownership only; it does not change the point command or last physical position.

Final movement release requires independent governing-signal Stop proof and healthy/fresh/CLEAR direction-release detection before clearing remaining route/signal/direction resources.

## 4. Logical I/O is separate from target binding

Author logical fields with:

- stable logical ID;
- channel (`command_input`, `field_feedback_input`, `plc_state_output`, `command_result_output`);
- authority (`dispatch`, `field_or_simulator`, `plc`);
- PLC writability;
- value/enum type;
- fail-safe value; and
- provenance.

Do not put IEC symbols, `%MW` locations, or Modbus registers in the logical interface document. The OpenPLC target allocator deterministically derives a binding containing logical channel/authority plus IEC symbol, memory word, IEC location, Modbus register, type, and PLC direction.

Target validation must prove:

- authority/writability matches channel;
- PLC-generated ST never assigns a `field_feedback_input`;
- every proof dependency resolves only to `field_feedback_input` owned by `field_or_simulator`;
- range counts equal canonical logical-field inventory;
- ranges do not overlap; and
- owner/target codes are unique, non-zero, and cannot collide with the no-owner sentinel.

## 5. Independent proving and freshness

A command, owner word, PLC state, or output read-back cannot prove its own result. `PROVED` requires named independent field/simulator feedback.

For simulated feedback:

- run a separate adapter process that reads PLC commands and writes only feedback, health, and heartbeat fields;
- derive freshness in PLC logic from heartbeat movement plus a reviewed stale interval;
- test delay, refusal, wrong value, frozen heartbeat, heartbeat wrap, recovery, and adapter death;
- never give the test harness access to PLC internal variables or permission to write PLC-owned state/result/owner words.

## 6. Command correlation and achieved condition

A compact command envelope may use five contiguous words: sequence, kind, target, argument, and strobe. Send it in one FC16 request.

Result words should expose at least:

- acknowledged sequence;
- lifecycle;
- rejection reason;
- target; and
- achieved condition.

Use achieved conditions such as route locked, release pending, route released, proved point/signal state, and recovery-inhibit cleared. Do not let one generic “proved target” conflate these outcomes.

Protocol rules:

1. Detect only strobe-set commands whose sequence differs from acknowledged sequence.
2. Treat UINT sequence modulo 65536; never reuse the currently acknowledged value.
3. Separate receipt, acceptance, execution, rejection/timeout, and proved completion.
4. Keep terminal result visible for at least one PLC scan ordinal.
5. Test wrap with a separately compiled synthetic fixture from the same renderer/IR; do not write PLC-owned ACK state or add a production-only test hook.

## 7. Restart and fail-closed controller state

Use a controller lifecycle such as `STARTING → RECOVERY_HELD → OPERATIONAL`.

On every cold start/restart:

- command signals Stop and authority restrictive;
- initialize only PLC-owned sampling/freshness state;
- never initialize or overwrite external feedback words;
- disarm/acknowledge retained command payload without replaying it;
- treat volatile owner zero as “not reconstructed,” not clearance proof; and
- reject route, point, and permissive-signal commands while recovery-held.

A guarded recovery RESET may clear only the global recovery inhibit after one current snapshot proves all configured detections CLEAR/healthy/fresh, all signals independently Stop/healthy/fresh, point correspondence valid, and direction state non-contradictory. RESET never clears an owned route/resource and never advances release.

## 8. Route-entry expiry and race precedence

Keep route setup timeout, API/client timeout, route-entry expiry, cancellation, feedback stale interval, proving timeout, and release clear hold as separately named semantics. Never use one generic timeout.

For the accepted 120-second route-entry expiry:

- start it only after the route is locked;
- cancel it on first valid route-entry occupancy and enter movement-based release;
- if valid entry and expiry occur in the same scan snapshot, entry wins;
- on no-entry expiry, command governing signal Stop and retain all locks;
- release only on a later scan after independent Stop proof plus healthy/fresh/CLEAR approach detection;
- otherwise remain held.

Unapproved values from presentations or historical code are examples, not defaults. Each point, signal, heartbeat, and release timer needs reviewed provenance.

## 9. Direct-operation guards

Direct maintenance-style commands must not bypass interlocking:

- signal Stop is restrictive;
- a permissive signal request requires the matching already-owned route in a proved operational state and exactly that route's reviewed aspect;
- direct point movement requires controller operational, target unowned, every related route IDLE, related detections CLEAR/healthy/fresh, and independent correspondence proof.

## 10. Two-stage OpenPLC address evidence

Treat source-code mapping documentation as a candidate contract until verified against the exact deployed image.

Stage 1 — before target generation:

- compile/run a small probe on the exact image;
- use FC06/FC03 for one word;
- use one FC16 request plus FC03 read-back for five contiguous words;
- capture image digest, function codes, PDU addresses, values, compile/start logs, and restart observations;
- confirm the observed `%MWn` to holding-register mapping.

Stage 2 — before completion/push:

- run the complete generated ST;
- compare JSON bindings to live FC03 reads at every allocated range's first and last binding and the global highest binding;
- verify the real FC16 command envelope;
- retain PDU evidence;
- only then mark complete-artifact range evidence confirmed and regenerate final tracked outputs.

This split avoids a circular gate: the complete address range cannot be proved before the complete program exists, but release cannot be claimed before that proof passes.

## 11. Runtime and acceptance gates

Use the deployed image and the same upload/autostart mechanism as the real testbed, but prefer the least complex isolated orchestration required by the current repository; do not make product Compose a prerequisite when direct Docker is the approved path.

Verification is not health-only. Require:

- generated ST upload and compile success;
- running/healthy state;
- restrictive startup and externally orchestrated restart/de-replay;
- independent feedback-adapter behavior and failure;
- UNKNOWN/invalid/stale inputs;
- successful route setup/proof;
- entry/expiry race and one real wall-clock expiry;
- ordered sectional and guarded final release;
- conflicts and direction lock;
- cancel/reset behavior;
- direct point/signal guards;
- protocol replay/skip/wrap; and
- a parameterized setup/entry/release path for every reviewed route.

Any skip, xfail, registry failure, compile failure, health-only result, missing PDU trace, incomplete engineering, or incomplete range evidence blocks completion/push. A temporary image/registry outage is an execution blocker, not a durable claim that the tool or target is broken.

## 12. Planning and verification discipline

- Run independent grills for data/I/O, PLC safety state, and runtime/evidence before asking for implementation approval.
- Integrate only findings that still apply to the latest plan snapshot; reviewers may have inspected an earlier concurrent draft.
- Keep newly derived clarifications separate from already accepted requirements so the user can approve them explicitly.
- Preserve the concise integrated review and verification under the canonical plan evidence directory; raw background-agent cache is not durable evidence.
- Verify tracked scope, tests, lint, types, package build, diff checks, and knowledge validation before presenting the approval checkpoint.
- Report pre-existing formatting or quality failures precisely; do not modify unrelated production files merely to make a documentation review look green.
