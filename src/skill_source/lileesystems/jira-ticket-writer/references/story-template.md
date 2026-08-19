# Story Ticket Template

Use for feature-level work that delivers user-facing or system-level capability: new features, significant behavior changes, new integrations, design-level improvements, or work that may spawn multiple sub-tasks. Stories describe *what* the system should do from a higher perspective, while Tasks break down the *how*.

## Structure

Every Story ticket has exactly three sections in this order:

1. **Introduction** (with two required subsections: Why and Scenario)
2. **Requirements**
3. **Revision**

---

## Section 1: Introduction

The Introduction has two required subsections — `## Why` and `## Scenario` — followed by optional supporting context (2-4 sentences). The big-section header is `# Introduction` (do not skip it).

### Subsection: Why

- One sentence
- Externally readable — any engineer, PM, or cross-team person can understand without context
- No internal jargon

**Good examples:**
- "Dispatchers need a way to set a temporary speed limit on a track section so vehicles passing through automatically slow down."
- "Vehicles experiencing a critical fault need a remote-operated return-to-yard procedure to clear the line for other traffic."
- "Operators need to monitor real-time ARK Code DOM levels per vehicle to detect degraded autopilot conditions."

### Subsection: Scenario

- One-line walkthrough from the user's perspective
- Often pulled directly from the Confluence Epic design doc's Story Breakdown
- Describes what *doing this Story* looks like in practice — the demo line

**Good examples:**
- "Dispatcher creates a Bulletin → manually toggles Enable On/Off → edits content → Hard-deletes."
- "Vehicle reports DOM 10 → Faramund dispatches Felicia → Felicia disengages autopilot → vehicle returns to AV1 block-by-block."
- "Vehicle status hub publishes new ARK Code → MMS displays the corresponding DOM level on the vehicle list within 5 seconds."

### Optional: Supporting Context

After the Why and Scenario subsections, add 2-4 sentences of supporting context if relevant:
- Reference source: meeting date, parent Epic ticket (SART-XXXX), Confluence design doc, related discussion
- Out-of-scope notes that distinguish this Story from sibling Stories under the same Epic
- Neutral, technical tone

### Full Introduction example

```markdown
# Introduction

## Why
Dispatchers need a way to set a temporary speed limit on a track section so vehicles passing through automatically slow down.

## Scenario
Dispatcher creates a Bulletin → manually toggles Enable On/Off → edits content → Hard-deletes.

This is Story 1.a of the TSR Epic (SART-1140), covering the foundational CRUD and manual control flow defined in the Path 2 scenario of the design doc. Out of scope here: Timer-based scheduling (Story 1.b) and conflict detection (Story 1.c).
```

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
- Use SafeART standard terminology: Mission Executor, Nibble Executor, ADS Agent, FSM, MA, DOM level, ARK Code, WSS, Faramund, Felicia, Bulletin, etc.
- No code snippets, no vague language, no speculation
- For Stories, requirements should be at a capability level — they can later be decomposed into Task-level sub-tickets

### Format

```markdown
**R1:** [High-level capability or behavior]
- **R1.1:** [Specific aspect or condition]
- **R1.2:** [Specific aspect or condition]

**R2:** [Second capability block]
- **R2.1:** [Sub-requirement]
- **R2.2:** [Sub-requirement]

**R3:** [Acceptance / validation criteria]
- **R3.1:** [Acceptance condition]
- **R3.2:** [Acceptance condition]
```

### Example

```markdown
**R1:** The Faramund dispatcher shall automatically initiate the breakdown handling SOP when a vehicle reports a critical fault.
- **R1.1:** The dispatcher shall establish a 3-way WebSocket handshake between itself, the Safety Server, and the field operator (Felicia) before proceeding with any movement authorization.
- **R1.2:** If the field operator does not connect within 120 seconds, the dispatcher shall escalate to the OCC (Operations Control Center) and halt the SOP.

**R2:** The dispatcher shall authorize return movement on a block-by-block basis.
- **R2.1:** Each block authorization shall require confirmation from both the field operator and the Safety Server before the vehicle proceeds.
- **R2.2:** The dispatcher shall track the vehicle's progress and update the MMS dashboard in real time.

**R3:** The automated breakdown handling shall be validated end-to-end.
- **R3.1:** A simulated breakdown scenario shall complete the full 14-step SOP without manual intervention.
- **R3.2:** The system shall correctly handle the case where the field operator disconnects mid-SOP.
```

---

## Section 3: Revision

```markdown
| Date       | Description     | Author  |
| ---------- | --------------- | ------- |
| YYYY-MM-DD | Initial Version | Preston |
```

- Use today's date, first entry "Initial Version", author "Preston"
- When updating, add a new row — never remove previous rows

---

## Full Template

```markdown
# [Short and Meaningful Title — describe the capability]

# Introduction

## Why
[One sentence. Externally readable. No jargon.]

## Scenario
[One-line walkthrough from the user's perspective.]

[Optional 2-4 sentences of supporting context with reference.]

# Requirements

**R1:** [High-level capability]
- **R1.1:** [Specific aspect]
- **R1.2:** [Specific aspect]

**R2:** [Second capability]
- **R2.1:** [Sub-requirement]

**R3:** [Acceptance / validation criteria]
- **R3.1:** [Acceptance condition]
- **R3.2:** [Acceptance condition]

# Revision

| Date       | Description     | Author  |
| ---------- | --------------- | ------- |
| YYYY-MM-DD | Initial Version | Preston |
```
