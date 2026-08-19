# TSR Diagram Review and Rendering Notes

Use this when producing reviewable TSR / Form A / Form B diagram packs from Mermaid.

## When to split diagrams

Prefer separate diagrams for:
- shared bulletin lifecycle / status model
- shared runtime evaluation
- type-specific runtime flows (`TSR`, `Form A`, `Form B`)
- GUI bulletin operation flow when the review needs to explain create / enforce / disable / edit behavior

Do not hide dispatcher-operational rules inside backend runtime diagrams if a dedicated GUI flow would be clearer.

## GUI operation flow facts accepted in review

These were explicitly accepted by Preston for diagramming:

- A newly created bulletin is **disabled / Not Enforced**.
- A bulletin only becomes operational after **enforce**.
- While a bulletin is enforced, **no modification is allowed**.
- To modify, dispatcher must **disable -> edit -> re-enforce**.
- For temporary extension of a Form A bulletin, the operationally safer/common pattern is often:
  - create a **new** bulletin,
  - use the **same milepost**,
  - set new `StartTime = current bulletin EndTime`,
  - extend the new `EndTime` forward.

If you want to elevate that extension pattern from GUI workflow note to normative product behavior, confirm with Preston first.

## Mermaid rendering verification pitfall

A PNG existing on disk is **not enough** evidence that Mermaid rendered successfully.

Add an explicit check for Mermaid error output such as:
- `Syntax error in text`

Recommended verification rule for local HTML -> Playwright screenshot pipelines:
1. regenerate HTML wrappers from `.mmd`
2. open each HTML in browser automation
3. wait for `#capture svg`
4. inspect rendered text for Mermaid syntax-error banners
5. fail verification if an error banner is present
6. only then save / accept the PNG
7. verify one PNG exists per Mermaid source file

## Why this reference exists

This note captures two failure modes that caused review churn:
- diagrams drifted from source into invented summary wording
- Mermaid generated a screenshot of its own syntax-error banner, and a naive file-exists check failed to catch it
