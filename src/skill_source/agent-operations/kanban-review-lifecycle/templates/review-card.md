# Review card fields

Review mode: same-card | separate-child
Reviewed identity: <task, parent, commit, tree, or artifact digest>
Authorized scope: <exact boundary>
Acceptance criteria: <checkable outcomes>
Stop conditions: <identity mismatch, concurrent mutation, or blocked evidence>
Evidence required: <commands, exit codes, material results, and scope checks>

Verdict: APPROVED | CHANGES_REQUESTED
Severity counts: Critical <n> | Important <n> | Minor <n> | Cannot Verify <n>
Findings: <actionable evidence with stable locators, or none>
Concerns: <non-blocking risks, or none>
Recommended next action: <coordinator-owned next step>

Terminal transition:
- Same-card `APPROVED` → complete the reviewed card.
- Same-card blocking findings → request changes on the reviewed card.
- Separate-child verdict → complete this review child with the verdict and evidence. Do not request changes against the completed parent or create another review lane.

Reviewer boundary: do not delegate, redesign the graph, implement corrections, merge, publish, deploy, or apply changes.
