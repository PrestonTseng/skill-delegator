# Review card fields

Review mode: same-card | separate-child
Final artifact identity: <task, parent, exact commit/head plus tree, or immutable artifact digest>
Authorized scope: <exact boundary>
Acceptance criteria: <checkable outcomes>
Stop conditions: <identity mismatch, concurrent mutation, or blocked evidence>
Evidence required: <commands, exit codes, material results, and scope checks>
Verification surface: <same runtime/UI/integration surface, or unavailable with reason>

Review verdict: APPROVED | CHANGES_REQUESTED
Verification verdict: VERIFIED | NOT_VERIFIED | INCONCLUSIVE
Severity counts: Critical <n> | Important <n> | Minor <n> | Cannot Verify <n>
Findings: <actionable evidence with stable locators, or none>
Concerns: <non-blocking risks, or none>
Recommended next action: <coordinator-owned next step>

Terminal transition:
- Same-card `APPROVED` → complete the reviewed card.
- Same-card blocking findings → request changes on the reviewed card.
- Separate-child verdict → complete this review child with the verdict and evidence. Do not request changes against the completed parent or create another review lane.

Reviewer boundary: do not delegate, redesign the graph, implement corrections, merge, publish, deploy, or apply changes.

Identity rule: any change to the Final artifact identity makes both prior verdicts stale. Rerun the review and verification evidence against the new identity. Proxy tests do not replace an available same surface; if that surface is unavailable, use `INCONCLUSIVE`.
