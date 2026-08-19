# Bug Ticket Template

## Structure

Every Bug ticket description has exactly three sections in this order:

1. **Actual Behavior / Reproduce Steps**
2. **Expected Behavior**
3. **Revision**

Additionally, Bug tickets require Jira metadata fields for **Summary** and **Environment**.

---

## No Duplicate Metadata in Description

Do **not** repeat Jira field values inside the description:

- Do **not** start the description with the ticket title/summary. The Jira Summary field already stores it.
- Do **not** include Build Version or Environment as standalone lines at the top of the description. Put them in the Jira Environment field instead.
- If build/environment context is relevant to reproduction, mention it once naturally inside Actual Behavior, not as duplicated metadata.

If the user doesn't specify environment and build version, ask for them before creating the Bug because the Jira Environment field is required.

---

## Section 1: Actual Behavior / Reproduce Steps

- Clearly describe the observed incorrect behavior
- Include specific steps to reproduce when possible
- Include relevant log snippets in fenced code blocks
- Reference specific components, functions, or modules
- Be precise about the conditions under which the bug occurs

### Content to include:
- What triggers the issue
- Observable symptoms (error messages, incorrect output, unexpected state)
- Relevant log excerpts in code blocks
- Frequency: Reproducible / Intermittent / One-time

### Example

```markdown
# Actual Behavior / Reproduce Steps:

When the vehicle is not in its designated departure position, an error log appears during mission execution in `_validate_ads_position` as follows:

\`\`\`
thalos.core.mission_executor.2025-12-01.207U.T3-E:N2W-N:1 - WARNING - N/A - Validate ADS position attempt 14/24 failed: Vehicle 1.900.0002.01 is in block W6T, expected W6T
\`\`\`

The expected block ID field is incorrectly populated with the vehicle's current block ID instead of the mission's starting station block ID. This occurs every time a mission is initiated while the vehicle is already at the departure station.
```

---

## Section 2: Expected Behavior

- 1-3 sentences
- Describe the correct outcome or behavior
- Be specific about expected values, states, or outputs
- No implementation details — focus on "what" not "how"

### Example

```markdown
# Expected Behavior:

The expected block ID in the `_validate_ads_position` log should reflect the mission's starting station block ID, not the vehicle's current position. When the vehicle is already at the correct departure position, validation should pass immediately.
```

---

## Section 3: Revision

Must be a Markdown table with bold headers:

```markdown
# Revision

| **Date** | **Description** | **Author** |
| --- | --- | --- |
| YYYY-MM-DD | Initial version | <your-name> |
```

- Use today's date
- First entry is always "Initial version"
- Author is "<your-name>"
- Table headers should be bold

---

## Severity Guidelines

| Severity | When to use |
| --- | --- |
| **Sev-0** | System down, data loss, or safety impact |
| **Sev-1** | Major feature broken, no workaround |
| **Sev-2** | Feature impaired but workaround exists |
| **Sev-3** | Minor issue, cosmetic, or edge case |

---

## Good Bug Titles

- Be specific about what's wrong and where
- Include the component or function name when relevant

**Good:**
- "Mission Executor fails to transition to IDLE state after mission abort"
- "The error log for `_validate_ads_position` contains incorrect expected block ID"
- "ADS Agent reports stale vehicle position after route re-authorization"

**Bad:**
- "Bug in validation" (too vague)
- "Error message wrong" (no specificity)

---

## Full Template

```markdown
# Actual Behavior / Reproduce Steps:

[Describe the observed incorrect behavior. Mention build/environment only if needed as reproduction context, not as repeated metadata.]

[Steps to reproduce if applicable:]
1. [Step 1]
2. [Step 2]
3. [Step 3]

\`\`\`
[Relevant log snippet if applicable]
\`\`\`

[Additional context about the log or behavior.]

# Expected Behavior:

[1-3 sentences describing correct behavior.]

# Revision

| **Date** | **Description** | **Author** |
| --- | --- | --- |
| YYYY-MM-DD | Initial version | <your-name> |
```
