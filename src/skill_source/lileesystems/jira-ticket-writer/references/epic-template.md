# Epic Ticket Template

Use for Jira Epic tickets. The Epic is a stub that points to the Confluence design doc — Confluence is the source of truth, the Jira Epic is the umbrella for child Story tickets.

The Epic ticket itself is intentionally short. Do not duplicate the Confluence content into Jira.

## Structure

Every Epic ticket has exactly three sections in this order:

1. **Summary**
2. **Design Doc**
3. **Revision**

---

## Section 1: Summary

- 1-3 sentences only
- Pull from the **Why** section of the Confluence design doc — this is the same one-line, externally readable framing
- May extend slightly to mention scope (one extra sentence) if helpful, but do not list features
- Externally readable: any engineer, PM, or cross-team person should understand without needing the design doc

### Good example

```markdown
# Summary

When an emergency happens (e.g., maintenance crew on track), dispatchers need a way to tell all vehicles passing a section to slow down before it becomes dangerous. This Epic covers the full TSR (Temporary Speed Restriction) capability across SafeART 0.19–0.21.
```

### Bad example

```markdown
# Summary

This Epic implements TSR Bulletin CRUD, Timer scheduling, conflict detection, MA push, Trackmap visualization, and overspeed alerts.
```

(Bad because: lists features instead of explaining purpose; reads like a story breakdown not a Why; too jargon-heavy for a cross-team reader.)

---

## Section 2: Design Doc

- Single line linking the source-of-truth Confluence page
- Bold "Source of truth:" prefix
- Format: Markdown link with the Confluence page title

### Example

```markdown
# Design Doc

**Source of truth:** [TSR — Temporary Speed Restriction](https://lileesystems.atlassian.net/wiki/spaces/SART/pages/3630465067)
```

If the Confluence page does not exist yet, do **not** open the Epic ticket. Route the user to `epic-design-doc` first — the Jira Epic with no design doc behind it is exactly the anti-pattern this skill avoids.

---

## Section 3: Revision

Standard revision table:

```markdown
# Revision

| Date | Description | Author |
| --- | --- | --- |
| YYYY-MM-DD | Initial Version | Preston |
```

- Use today's date
- First entry is always "Initial Version"
- Author is "Preston"
- Table headers should be bold

---

## Good Epic Titles

- **Match the Confluence design doc title** when possible — keeps the link unambiguous
- Use the product-level capability name (e.g., "TSR — Temporary Speed Restriction")
- Do **not** include phase, release, or sprint info in the title — those belong in the design doc's Cross-Release Plan

**Good:**
- "TSR — Temporary Speed Restriction"
- "Faramund Breakdown Handling SOP"
- "Manual Mode Cross-Day Operations"
- "Schedule Management Refactoring"

**Bad:**
- "TSR Implementation Phase 1" (don't include phase info)
- "Speed restriction stuff" (vague)
- "Carsten's TSR work" (don't include assignee)

---

## Full Template

```markdown
# [Epic Title — match Confluence design doc title]

# Summary

[1-3 sentences derived from the Confluence Why section. Externally readable, no jargon, no feature list.]

# Design Doc

**Source of truth:** [<Confluence page title>](<URL>)

# Revision

| Date | Description | Author |
| --- | --- | --- |
| YYYY-MM-DD | Initial Version | Preston |
```
