# Principle / Policy Spec Pages

Use this reference when a backlog/spec page defines shared principles, conventions, or governance rather than detailed runtime behavior.

## Trigger signals

- User says the page is only defining principles, common rules, or a convention.
- Detailed behavior belongs in downstream service/component design docs.
- The topic is about naming, MQTT topics, ownership, rollout order, or required documentation flow.
- User pushes back that the normal backlog skeleton is too large or too many sections.

## Recommended concise structure

1. `Why`
2. `Key Terms`
3. `Scope`
4. `Principles` / `Convention`
5. `Priority` or `Ownership` if applicable
6. `Required Development Flow`
7. `Design Document Requirements`
8. `Acceptance Criteria`
9. `Open Questions`
10. `References`
11. `Revision`

## Review posture

Run an internal/no-background grill against the draft. Ask:

- Can a reader with no domain background understand the core term?
- Are source-model phrases like "follow X where applicable" actionable?
- Is the page accidentally defining downstream implementation details?
- Are IDs and topic placeholders precisely defined?
- Are acceptance criteria verifiable as convention compliance rather than page-content checks?

## Example lesson from SafeART ARK Code

For a shared MQTT convention page, keep service-specific event catalogs, error-bit meanings, payload schemas, and implementation architecture out of the shared page. Put them in service-specific design documents. The shared page should define only the convention, priority/order, required downstream document contents, and acceptance gates.
