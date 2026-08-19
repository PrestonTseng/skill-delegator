# Task Ticket Template

Use for concrete, well-scoped work items: behavior fixes with known scope, refactoring, configuration changes, infrastructure work, CI/CD improvements, testing automation, or any implementation work where the outcome is clearly defined.

## Structure

Every Task ticket has exactly three sections in this order:

1. **Introduction**
2. **Requirements**
3. **Revision**

---

## Section 1: Introduction

- 2-4 sentences only
- Describe the problem background, observed phenomenon, or purpose of the change
- Neutral, technical tone
- Reference source when applicable: meeting date, another ticket (SART-XXXX), testing phase, etc.

**Good examples:**
- "Based on findings during <YOUR-BOARD>-XXXX, the Mission Executor does not properly handle the transition from EXECUTING to IDLE when a mission abort is triggered mid-nibble."
- "The Jenkins CI pipeline currently lacks E2E test integration for the Safety Server. This task covers adding Playwright-based E2E tests to the existing pipeline."
- "During alpha testing on <your-product> 0.18, we observed that the ARK Code display does not update when DOM level changes occur."

---

## Section 2: Requirements

### Formatting Rules (CRITICAL)

- ALL R numbers MUST be bold: `**R1:**`, `**R2:**`, `**R3:**`
- ALL sub-requirements MUST be bold: `**R1.1:**`, `**R1.2:**`, `**R2.1:**`
- Use a blank line between top-level R blocks
- Sub-requirements are indented with `- `

### Content Rules

- Describe behavior, logic, and conditions — NOT implementation
- Each requirement must be testable and verifiable
- Use standard terminology: Mission Executor, Nibble Executor, ADS Agent, FSM, MA, DOM level, ARK Code, WSS, etc.
- No code snippets, no vague language, no speculation

### Format

```markdown
**R1:** [High-level requirement statement]
- **R1.1:** [Specific sub-requirement]
- **R1.2:** [Specific sub-requirement]

**R2:** [Second requirement block]
- **R2.1:** [Sub-requirement]
- **R2.2:** [Sub-requirement]

**R3:** [Validation / testing requirements if applicable]
- **R3.1:** [Test condition]
- **R3.2:** [Test condition]
```

### Example

```markdown
**R1:** The Mission Executor shall transition to IDLE state within 5 seconds of receiving a mission abort command.
- **R1.1:** If the abort occurs during nibble execution, the Nibble Executor shall complete its current safe-stop procedure before the Mission Executor transitions.
- **R1.2:** The abort reason shall be logged with severity WARNING, including the mission ID and current FSM state at time of abort.

**R2:** The Safety Server shall notify the ADS Agent of the mission abort via the standard command interface.
- **R2.1:** The notification shall include the abort reason code and the last known vehicle position.
- **R2.2:** If the ADS Agent does not acknowledge within 10 seconds, the Safety Server shall retry up to 3 times before raising an alarm.
```

---

## Section 3: Revision

```markdown
| Date       | Description     | Author        |
| ---------- | --------------- | ------------- |
| YYYY-MM-DD | Initial Version | <your-name> |
```

- Use today's date, first entry "Initial Version", author "<your-name>"
- When updating, add a new row — never remove previous rows

---

## Full Template

```markdown
# [Short and Meaningful Title]

# Introduction

[2-4 sentences. Context, problem, or purpose. Reference source if applicable.]

# Requirements

**R1:** [High-level requirement]
- **R1.1:** [Sub-requirement]
- **R1.2:** [Sub-requirement]

**R2:** [Second requirement]
- **R2.1:** [Sub-requirement]

**R3:** [Validation/testing if needed]
- **R3.1:** [Test condition]

# Revision

| Date       | Description     | Author        |
| ---------- | --------------- | ------------- |
| YYYY-MM-DD | Initial Version | <your-name> |
```
