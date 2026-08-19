# Authorization-Loss Provenance Triage

Use this workflow when Thalos reports that a block lost authorization and the investigation must distinguish a TriOps occupancy input, a Thalos route command, and an upstream PLC/IXL or manual action.

## Core limitation

Thalos receives WSS Type 7 state, not provenance. Its block-change event contains only block ID, old/new occupancy, old/new authorization, and timestamp. It has no actor, source, command ID, or reason code. Thalos can prove the observed transition and correlate inputs, but it cannot identify a human or direct PLC/IXL actor without upstream audit data.

## Evidence workflow

1. **Anchor the exact transition**
   - Find the Thalos `Updated block <id> state` line.
   - Preserve nanosecond ordering and normalize display timezone.
   - Record occupancy and authorization separately; do not infer one from the other.

2. **Inspect raw WSS-agent register state immediately before and after**
   - Correlate `Block Occupancy` and `Block Authorized` for the same block.
   - Include the route's other controlled blocks and route status to determine whether the loss was isolated.

3. **Inspect TriOps Type 13 input at 5 Hz**
   - Topic: `/v1/triops/setting/<triops_id>`.
   - Decode occupancy using the ICD: `0 = OCCUPIED`, `1 = FREE`.
   - Capture at least the last payload before and first payload after the authorization transition.
   - If both report FREE and WSS occupancy remains FREE, a TriOps false-OCCUPIED report is contradicted by the preserved evidence.

4. **Inspect SS Type 8 route commands**
   - Topic: `/v1/ss/setting/<ss_id>`.
   - Decode route commands: `0 = UNSET/no command`, `4 = CLEAR_ROUTE`, `5 = REQUEST_AUTH`.
   - Correlate with Thalos `Requesting authorization`, `Revoking authorization`, route-owner, and superuser logs.
   - A Type 8 value of UNSET plus no Thalos revoke log rules out a Thalos-originated clear at that instant; it does not rule out direct PLC/IXL manipulation.

5. **Classify the result with explicit proof boundaries**
   - **Occupancy-driven supported:** TriOps reports OCCUPIED, WSS occupancy follows, then authorization drops in matching order.
   - **TriOps false occupancy contradicted:** TriOps and WSS occupancy stay FREE while authorization alone drops.
   - **Thalos command supported:** a matching request/clear command and owner log precede the state transition.
   - **Upstream inconsistency likely:** one controlled block loses authorization while occupancy stays FREE, peer blocks and route remain authorized, and no Thalos clear precedes it.
   - **Manual actor unknown:** status logs have no provenance. Require TriOps/management UI audit, PLC/OpenPLC change logs, or IXL command history to attribute a person or external client.

## Pitfalls

- Do not say “manual operation did not happen” merely because logs lack `manual`, `operator`, or `superuser` text.
- Do not treat a block-authorization loss as proof that occupancy changed.
- Do not use UI timestamps when raw logs provide finer ordering; races often occur within hundreds of milliseconds.
- Do not conflate the upstream authorization-loss cause with Thalos's downstream recovery behavior such as revoke/re-request or route timeout.
- When WSS-agent prints multiple register views or worker-thread dumps, identify the register/type and compare transitions rather than treating every repeated line as a new semantic event.

## Recommended report shape

1. What Thalos can and cannot know.
2. Exact pre/post TriOps and WSS values.
3. Matching Thalos/SS route commands, if any.
4. Ruled-out hypotheses.
5. Remaining attribution gap and the specific upstream audit source required.

## Confluence publication pattern

When the upstream authorization-loss cause remains unknown but the downstream Thalos mechanism is proven, make that separation visible in the report:

1. Set the RCA status to `ROOT CAUSE UNKNOWN`; do not promote an upstream candidate to root cause.
2. Name the unexplained authorization loss as the primary problem.
3. Use an evidence table with `Possibility | Result | Evidence`:
   - use `EXCLUDED` only when preserved evidence contradicts the candidate;
   - use `NO EVIDENCE` when logs contain no matching action but cannot exclude an unaudited path;
   - list unobservable PLC/IXL/manual paths separately as remaining unknowns.
4. Put the proven downstream sequence in its own timeline: authority scope, Nibble decision, awaited revoke, occupancy change, immediate request, WSS timeout, and block-exit reconciliation.
5. State that reproducing the downstream Thalos race does not reproduce the unknown upstream authorization loss.
6. If the user will add video later, keep a visible Video placeholder and prewrite the expected visual sequence. Do not leave the section empty or invent media.

This structure prevents two common errors: treating “no matching log” as proof of exclusion, and conflating a proven recovery defect with the unknown initiating fault.
